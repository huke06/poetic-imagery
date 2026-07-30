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


def _build_rag_prompt(concepts, poetries, artworks, question, shared_pids, mentioned_titles: set = None):
    """构建结构化 RAG 上下文：共享作品优先，用户提及的诗篇强制首部"""
    parts = []
    # ⭐ 用户明确提及的诗篇-绝对置顶
    if mentioned_titles:
        pinned = [p for p in poetries if p["title"] in mentioned_titles]
        if pinned:
            parts.append("【⚠ 用户明确问到的诗篇——以下内容必须仔细研读并引用】")
            for p in pinned:
                clauses = "；".join(c["clause"] for c in p["clauses"][:3])
                parts.append(f"《{p['title']}》（{p['dynasty']}·{p['author']}）全文：{p.get('content', '')[:200]}| 含象句：{clauses}")
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


def _find_mentioned_poems(db: Session, text: str) -> list[dict]:
    """扫描文本中《篇名》格式的引用或长标题（≥3字），返回该诗信息"""
    found = []
    # 先按《篇名》格式精确匹配
    import re
    cited = set(re.findall(r"《(.+?)》", text))
    # 再按长标题（≥3字）模糊匹配
    all_poems = db.query(Poetry).all()
    for p in sorted(all_poems, key=lambda x: -len(x.title)):
        if p.title in cited or (len(p.title) >= 3 and p.title in text):
            rels = db.query(ConceptPoetryRel).filter_by(poetry_id=p.id).all()
            concepts = []
            for r in rels:
                c = db.get(Concept, r.concept_id)
                if c:
                    concepts.append({"id": c.id, "name": c.name, "clause": r.clause})
            found.append({"poetry_id": p.id, "title": p.title, "author": p.author,
                          "dynasty": p.dynasty, "writing_type": p.writing_type,
                          "concepts": concepts, "content": p.content})
    return found


def _fulltext_search_poems(db: Session, query: str, limit: int = 6) -> list[dict]:
    """对诗文库做全文检索：标题/作者/内容匹配问题关键词"""
    # 提取有效关键词（≥2字的片段）
    import re
    words = [w for w in re.split(r"[，。！？；、：\s]+", query) if len(w) >= 2][:8]
    liked = []
    for w in words:
        liked.append(Poetry.title.like(f"%{w}%"))
        liked.append(Poetry.author.like(f"%{w}%"))
    results = []
    if liked:
        from sqlalchemy import or_
        rows = db.query(Poetry).filter(or_(*liked)).limit(limit * 2).all()
        for p in rows:
            if len(results) >= limit:
                break
            rels = db.query(ConceptPoetryRel).filter_by(poetry_id=p.id).all()
            concepts = []
            for r in rels:
                c = db.get(Concept, r.concept_id)
                if c:
                    concepts.append({"id": c.id, "name": c.name, "clause": r.clause})
            results.append({"poetry_id": p.id, "title": p.title, "author": p.author,
                           "dynasty": p.dynasty, "writing_type": p.writing_type,
                           "concepts": concepts, "content": p.content})
    return results


def ask(db: Session, question: str, context_msgs: list[dict] | None = None) -> dict:
    """context_msgs: [{"role": "user"|"ai", "content": "..."}] 完整对话历史"""
    concepts = _find_concepts(db, question)
    emotions = _find_emotions(question)

    mentioned_poems = _find_mentioned_poems(db, question)
    if mentioned_poems and not concepts:
        # 从提及的诗篇反推概念
        for mp in mentioned_poems:
            for c in mp["concepts"]:
                cc = db.get(Concept, c["id"])
                if cc and cc.id not in {x.id for x in concepts}:
                    concepts.append(cc)

    if not concepts:
        if llm.llm_available():
            sys_text = "你是古典诗词专家，直接作答。"
            if context_msgs:
                lines = [f"{'用户' if m['role']=='user' else '助手'}：{m['content'][:200]}" for m in context_msgs[-4:]]
                sys_text += "\n\n=== 对话历史 ===\n你必须根据历史解析指代。\n" + "\n".join(lines)
            prompt = (
                f"用户问题：「{question}」。请结合古典诗词知识直接回答（200 字内）。"
                "如果提到具体的诗篇名，请标注**《篇名》**格式。"
            )
            answer = llm.chat([
                {"role": "system", "content": sys_text},
                {"role": "user", "content": prompt},
            ])
            if answer:
                # 严格按《篇名》格式提取回答中明确引用的诗篇
                import re
                cited_titles = set(re.findall(r"《(.+?)》", answer))
                mp_refs = []
                for ct in cited_titles:
                    mp = db.query(Poetry).filter_by(title=ct).first()
                    if mp:
                        mp_refs.append({"poetry_id": mp.id, "title": mp.title, "author": mp.author,
                                        "dynasty": mp.dynasty, "writing_type": mp.writing_type,
                                        "clauses": [], "shared": False})
                return {"answer": answer, "source": "llm_free",
                        "references": {"concepts": [], "poetries": mp_refs[:6], "artworks": []}}

        all_c = db.query(Concept).all()
        names = "、".join(f"「{c.name}」" for c in all_c)
        examples = "、".join(f"「{c.name}」在古诗里有什么含义？" for c in all_c[:2])
        return {
            "answer": f"本地意象库收录：{names}。您的问题未命中。例如：{examples}",
            "source": "local",
            "references": {"concepts": [], "poetries": [], "artworks": []},
        }

    poetries, artworks, shared_pids = _gather_context(db, concepts, emotions)
    # 问题中提及的诗篇必须优先出现——强制置顶
    mentioned_in_q = _find_mentioned_poems(db, question)
    if mentioned_in_q:
        mentioned_titles = {m["title"] for m in mentioned_in_q}
        # 将提及的诗移到最前
        pinned = [p for p in poetries if p["title"] in mentioned_titles]
        rest = [p for p in poetries if p["title"] not in mentioned_titles]
        poetries = pinned + rest

    # ==== 全文搜索诗文库 ====
    search_results = _fulltext_search_poems(db, question, limit=5)
    existing_ids = {p.get("poetry_id") for p in poetries}
    for sr in search_results:
        if sr["poetry_id"] not in existing_ids:
            poetries.insert(0, {"poetry_id": sr["poetry_id"], "title": sr["title"],
                                "author": sr["author"], "dynasty": sr["dynasty"],
                                "writing_type": sr["writing_type"], "clauses": [],
                                "content": sr["content"], "shared": False, "from_search": True})
        for cc in sr.get("concepts", []):
            c = db.get(Concept, cc["id"])
            if c and c not in concepts:
                concepts.append(c)

    if llm.llm_available():
        # 对话历史放入 system 消息——LLM 必须根据历史解析当前问题中的指代（"他"、"这首诗"等）
        system_text = "你是严谨的古典诗词助手，只引用资料中出现的篇目，标注出处。若资料不足以回答，可回复[搜索:关键词]指令来查库。"
        if context_msgs:
            lines = []
            for m in context_msgs[-6:]:
                role = "用户" if m["role"] == "user" else "助手"
                lines.append(f"{role}：{m['content'][:250]}")
            if lines:
                system_text += (
                    "\n\n=== 对话历史 ===\n"
                    "用户当前提问可能引用历史内容(如 他/这首诗/该作者 等指代词), "
                    "你必须根据以下历史解析指代, 不得当作独立新问题。\n"
                    + "\n".join(lines)
                )
        mentioned_titles = {m["title"] for m in _find_mentioned_poems(db, question)}
        prompt = _build_rag_prompt(concepts, poetries, artworks, question, shared_pids, mentioned_titles)
        msgs = [{"role": "system", "content": system_text},
                {"role": "user", "content": prompt}]
        answer = llm.chat(msgs)
        if answer:
            # 引用过滤 + 答案提及的诗篇补充
            # 严格过滤：≥3字标题允许子串匹配，短标题（2字）只接受《篇名》格式或完整6字句读
            filtered_p = [p for p in poetries if f"《{p['title']}》" in answer or (
                len(p["title"]) >= 3 and p["title"] in answer) or any(
                len(c["clause"]) >= 6 and c["clause"] in answer for c in p["clauses"])]
            # 答案中明确引用了《篇名》格式的诗篇 → 从 DB 查补链接
            import re
            cited_titles = set(re.findall(r"《(.+?)》", answer))
            existing_titles = {p["title"] for p in filtered_p}
            for ct in cited_titles:
                if ct in existing_titles:
                    continue
                mp = db.query(Poetry).filter_by(title=ct).first()
                if mp:
                    filtered_p.append({"poetry_id": mp.id, "title": mp.title,
                                       "author": mp.author, "dynasty": mp.dynasty,
                                       "writing_type": mp.writing_type, "clauses": [],
                                       "content": mp.content, "shared": False})
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
