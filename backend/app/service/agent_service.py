# -*- coding: utf-8 -*-
"""轻量 RAG 智能助手 v2：精准检索 + 共现推导 + 引用溯源

流程：
1. 从问题中提取意象关键词（意象名/别称/单个汉字）与情感关键词
2. SQL 检索：意象本体 + 关联名句（含共现作品交叉推导）+ 对应古画
3. LLM 生成时将共享作品置于上下文首部，强调引用格式
4. 返回回答 + 精确引用来源（诗文/古画/意象）
"""
import random
import re
from collections import OrderedDict

from sqlalchemy.orm import Session

from ..models import Artwork, Concept, ConceptArtworkRel, ConceptPoetryRel, Poetry
from ..utils import llm
from .tone_service import poem_tones

# 情感关键词归一化 → 标准情感标签
EMOTION_KEYWORDS = {
    "思乡": ["思乡", "故乡", "家乡", "故园", "想家", "乡愁"],
    "怀人": ["怀人", "思念", "怀念", "相思", "想念", "悼亡"],
    "孤寂": ["孤寂", "孤独", "寂寞", "孤单", "清冷", "独处"],
    "时空永恒": ["永恒", "时空", "宇宙", "时间", "古今", "哲学"],
    "怀古": ["怀古", "咏史", "兴亡", "兴废", "古迹", "六朝"],
    "落寞": ["落寞", "萧瑟", "凄凉", "苍茫", "荒凉", "惆怅"],
    "时光流逝": ["时光", "岁月", "流逝", "迟暮", "黄昏", "年华"],
    "离愁": ["离愁", "离别", "送别", "分别", "离人", "断肠", "天涯"],
    "苍凉": ["苍凉", "苍茫", "悲壮", "荒凉", "边塞"],
    "豪迈": ["豪迈", "壮烈", "激昂", "慷慨"],
    "惜春": ["惜春", "春景", "感春", "伤春"],
    "厌战": ["厌战", "反战", "征战", "征人"],
}


def _find_concepts(db: Session, text: str) -> list[Concept]:
    """按意象名/别称匹配问题中提到的意象（支持单字匹配如'月''雁'）"""
    found: OrderedDict[int, Concept] = OrderedDict()
    for c in db.query(Concept).all():
        names = [c.name] + [a for a in (c.aliases or "").split(",") if a]
        # 先用完整词匹配
        if any(n and n in text for n in names if len(n) >= 2):
            found[c.id] = c
            continue
        # 再用单字匹配（更松）
        single_chars = [n for n in names if len(n) == 1]
        if single_chars and any(ch in text for ch in single_chars):
            found[c.id] = c
    return list(found.values())


def _find_emotions(text: str) -> list[str]:
    hits = []
    for tag, words in EMOTION_KEYWORDS.items():
        if any(w in text for w in words):
            hits.append(tag)
    return hits


def _gather_context(db: Session, concepts: list[Concept], emotions: list[str]):
    """检索全量关联数据，并在多意象场景下推导共享作品"""
    all_poetries: dict[int, dict] = {}   # poetry_id → {poetry info + clauses}
    concept_poetry_map: dict[int, set[int]] = {}  # concept_id → set of poetry_ids
    artworks = []

    for c in concepts:
        concept_poetry_map.setdefault(c.id, set())
        rels = db.query(ConceptPoetryRel, Poetry).join(Poetry, ConceptPoetryRel.poetry_id == Poetry.id).filter(
            ConceptPoetryRel.concept_id == c.id
        ).order_by(ConceptPoetryRel.is_classic.desc(), ConceptPoetryRel.weight.desc()).all()

        for rel, p in rels:
            concept_poetry_map[c.id].add(p.id)
            entry = all_poetries.setdefault(p.id, {
                "poetry_id": p.id, "title": p.title, "author": p.author, "dynasty": p.dynasty,
                "writing_type": p.writing_type, "content": p.content, "clauses": [],
            })
            entry["clauses"].append({
                "clause": rel.clause, "emotion": rel.emotion, "is_classic": rel.is_classic,
                "weight": rel.weight, "concept_id": c.id, "concept_name": c.name,
            })

        arel = db.query(ConceptArtworkRel, Artwork).join(
            Artwork, ConceptArtworkRel.artwork_id == Artwork.id
        ).filter(ConceptArtworkRel.concept_id == c.id).order_by(
            ConceptArtworkRel.weight.desc()).limit(3).all()
        for rel, a in arel:
            artworks.append({
                "id": a.id, "name": a.name, "artist": a.artist, "dynasty": a.dynasty_period or a.dynasty,
                "thumb_url": a.thumb_url, "relation_desc": rel.relation_desc,
            })

    # 识别共享作品（多意象场景）
    shared_pids = set()
    if len(concepts) >= 2:
        pids_per_concept = list(concept_poetry_map.values())
        shared_pids = pids_per_concept[0].intersection(*pids_per_concept[1:])

    # 按情感/权重排序，共享作品优先
    ranked = []
    for pid, entry in all_poetries.items():
        is_shared = pid in shared_pids
        clauses = entry["clauses"]
        has_classic = any(c["is_classic"] for c in clauses)
        max_weight = max((c["weight"] for c in clauses), default=1)
        emo_match = any(c["emotion"] in emotions for c in clauses) if emotions else False
        rank = (int(is_shared) * 1000 + int(has_classic) * 100 + max_weight * 10 + int(emo_match) * 5)
        ranked.append((rank, entry, is_shared))
    ranked.sort(key=lambda x: x[0], reverse=True)

    poetries = [{"poetry_id": e["poetry_id"], "title": e["title"], "author": e["author"],
                 "dynasty": e["dynasty"], "writing_type": e["writing_type"],
                 "clauses": e["clauses"], "content": e["content"], "shared": shared}
                for _, e, shared in ranked]

    return poetries, artworks, shared_pids


def _build_rag_prompt(concepts, poetries, artworks, question, shared_pids):
    """构建结构化 RAG 上下文：共享作品优先"""
    parts = []
    # 意象本体
    for c in concepts:
        parts.append(f"【意象·{c.name}】{c.poetic_meaning[:120]} 情感标签：{c.emotion_tags}")
    # 共享作品
    if shared_pids:
        shared_info = [p for p in poetries if p["shared"]][:6]
        if shared_info:
            parts.append("【⚠ 以下作品同时包含这些意象——优先引用】")
            for p in shared_info:
                clauses = "；".join(c["clause"] for c in p["clauses"][:3])
                parts.append(f"《{p['title']}》（{p['dynasty']}·{p['author']}）：{clauses}")
    # 非共享名句
    unshared = [p for p in poetries if not p["shared"]][:8]
    if unshared:
        parts.append(f"【其他关联名句】")
        for p in unshared:
            c = p["clauses"][0]
            parts.append(f"《{p['title']}》（{p['dynasty']}·{p['author']}）「{c['clause']}」（{c['emotion']}）")
    # 古画
    if artworks:
        parts.append("【关联古画】")
        for a in artworks[:3]:
            parts.append(f"《{a['name']}》（{a['dynasty']}·{a['artist']}）")
    prompt = (
        "你是古诗词意象专家。请基于以下资料回答用户问题。\n"
        "**务必做到**：① 引用的每首诗的标题都必须在上面资料中出现过，不得编造；"
        "② 优先引用【⚠ 共享作品】里的篇目；③ 使用引用格式：**《篇名》**（朝代·作者）。"
        "若资料不足以完全回答，可有限补充你的常识但须说明。语言典雅简洁，分条列点。\n\n"
        + "\n".join(parts)
        + f"\n\n【用户问题】{question}"
    )
    return prompt


def ask(db: Session, question: str, context_history: list[str] | None = None) -> dict:
    concepts = _find_concepts(db, question)
    emotions = _find_emotions(question)

    if not concepts:
        if llm.llm_available():
            prompt = (
                f"用户问题：「{question}」。本地意象库未命中。请结合古典诗词知识直接回答（200 字内）。"
                "末尾加说明：*（本回答由大模型知识生成，未锚定本地意象库）*"
            )
            answer = llm.chat([
                {"role": "system", "content": "你是古典诗词专家，直接作答。"},
                {"role": "user", "content": prompt},
            ])
            if answer:
                return {"answer": answer, "source": "llm_free",
                        "references": {"concepts": [], "poetries": [], "artworks": []}}

        all_c = db.query(Concept).all()
        names = "、".join(f"「{c.name}」" for c in all_c)
        examples = "、".join(f"「{c.name}」在古诗里有什么含义？" for c in all_c[:2])
        return {
            "answer": f"本地意象库收录：{names}。您的问题未命中。例如：{examples}",
            "source": "local",
            "references": {"concepts": [], "poetries": [], "artworks": []},
        }

    poetries, artworks, shared_pids = _gather_context(db, concepts, emotions)

    if llm.llm_available():
        # 拼接历史上下文
        history = ""
        if context_history:
            history = "【最近对话】\n" + "\n".join(f"用户：{q[:200]}" for q in context_history[:4]) + "\n\n"
        prompt = _build_rag_prompt(concepts, poetries, artworks, question, shared_pids)
        msgs = [{"role": "system", "content": "你是严谨的古典诗词助手，只引用资料中出现的篇目，标注出处。可以结合上面的对话历史理解用户意图。"}]
        if history:
            msgs.append({"role": "user", "content": history + prompt})
        else:
            msgs.append({"role": "user", "content": prompt})
        answer = llm.chat(msgs)
        if answer:
            # 引用过滤：出现在回答中的篇目标题
            filtered_p = [p for p in poetries if p["title"] in answer or any(
                c["clause"] in answer for c in p["clauses"])]
            filtered_a = [a for a in artworks[:3] if a["name"] in answer]
            return {
                "answer": answer, "source": "llm",
                "references": {
                    "concepts": [{"id": c.id, "name": c.name} for c in concepts],
                    "poetries": filtered_p[:8], "artworks": filtered_a or artworks[:3],
                },
            }
        # LLM 失败回落
        return {
            "answer": _local_answer(question, concepts, emotions, poetries, shared_pids),
            "source": "local",
            "references": {"concepts": [{"id": c.id, "name": c.name} for c in concepts],
                           "poetries": poetries[:8], "artworks": artworks[:3]},
        }

    return {
        "answer": _local_answer(question, concepts, emotions, poetries, shared_pids),
        "source": "local",
        "references": {"concepts": [{"id": c.id, "name": c.name} for c in concepts],
                       "poetries": poetries[:8], "artworks": artworks[:3]},
    }


def _local_answer(question, concepts, emotions, poetries, shared_pids):
    parts = []
    for c in concepts:
        emo = "、".join((c.emotion_tags or "").split(","))
        parts.append(f"「{c.name}」{c.poetic_meaning.split('。')[0]}。核心情感：{emo}")
    if shared_pids:
        shared = [p for p in poetries if p["shared"]][:4]
        lines = "\n".join(
            f"·《{p['title']}》（{p['dynasty']}·{p['author']}）—— "
            + "；".join(c["clause"] for c in p["clauses"]) for p in shared
        )
        parts.append(f"同时包含这些意象的作品：\n{lines}")
    else:
        top = poetries[:5]
        if top:
            lines = "\n".join(
                f"·「{p['clauses'][0]['clause']}」——{p['dynasty']}·{p['author']}《{p['title']}》" for p in top
            )
            parts.append(f"经典名句：\n{lines}")
    if concepts:
        c0 = concepts[0]
        parts.append(f"演变：{c0.name}意象起源于{c0.origin_dynasty}，鼎盛于{c0.peak_dynasty}。{c0.description[:80]}……")
    parts.append("（以上由本地意象知识库生成，所有引用可溯源。）")
    return "\n\n".join(parts)
