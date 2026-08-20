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
from . import embedding_index
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
    """构建带 [n] 角标的 RAG 上下文，返回 (prompt, refs)

    refs 每个元素带稳定 idx，用于回答后把 LLM 引用的 [n] 确定性映射回真实链接。
    """
    refs: list[dict] = []
    parts = []

    def add_ref(**kw):
        idx = len(refs) + 1
        kw["idx"] = idx
        refs.append(kw)
        return idx

    # ⭐ 用户明确提及的诗篇-绝对置顶
    if mentioned_titles:
        pinned = [p for p in poetries if p["title"] in mentioned_titles]
        if pinned:
            parts.append("【⚠ 用户明确问到的诗篇——以下内容必须仔细研读并引用】")
            for p in pinned:
                clauses = "；".join(c["clause"] for c in p["clauses"][:3])
                idx = add_ref(type="poetry", poetry_id=p["poetry_id"], title=p["title"],
                              author=p["author"], dynasty=p["dynasty"], clause=clauses)
                parts.append(f"[{idx}]《{p['title']}》（{p['dynasty']}·{p['author']}）全文：{p.get('content', '')[:200]}| 含象句：{clauses}")
    # 意象本体
    if concepts:
        parts.append("【意象】")
        for c in concepts:
            idx = add_ref(type="concept", concept_id=c.id, name=c.name)
            parts.append(f"[{idx}]「{c.name}」{c.poetic_meaning[:120]} 情感标签：{c.emotion_tags}")
    # 共享作品（排除已在上面置顶提及的，避免重复）
    _mt = mentioned_titles or set()
    if shared_pids:
        shared_info = [p for p in poetries if p["shared"] and p["title"] not in _mt][:6]
        if shared_info:
            parts.append("【⚠ 以下作品同时包含这些意象——优先引用】")
            for p in shared_info:
                clauses = "；".join(c["clause"] for c in p["clauses"][:3])
                idx = add_ref(type="poetry", poetry_id=p["poetry_id"], title=p["title"],
                              author=p["author"], dynasty=p["dynasty"], clause=clauses)
                parts.append(f"[{idx}]《{p['title']}》（{p['dynasty']}·{p['author']}）：{clauses}")
    # 非共享名句（排除已置顶提及的，避免重复）
    unshared = [p for p in poetries if not p["shared"] and p["title"] not in _mt][:10]
    if unshared:
        parts.append("【其他关联名句】")
        for p in unshared:
            c = p["clauses"][0]
            idx = add_ref(type="poetry", poetry_id=p["poetry_id"], title=p["title"],
                          author=p["author"], dynasty=p["dynasty"], clause=c["clause"])
            parts.append(f"[{idx}]《{p['title']}》（{p['dynasty']}·{p['author']}）「{c['clause']}」（{c['emotion']}）")
    # 古画
    if artworks:
        parts.append("【关联古画】")
        for a in artworks[:3]:
            idx = add_ref(type="artwork", artwork_id=a["id"], name=a["name"],
                          artist=a["artist"], dynasty=a["dynasty"])
            parts.append(f"[{idx}]《{a['name']}》（{a['dynasty']}·{a['artist']}）")
    prompt = (
        "你是「诗象万千」的古诗词意象专家，擅于陪人读诗、解诗、探索意象。请基于以下资料回答用户问题。\n"
        "回答要求：\n"
        "① 结构：先给一句凝练的核心结论，再分层展开（含义→情感色彩→代表诗句→演变或延伸），最后可自然收束；\n"
        "② 引用诗篇必须用《篇名》（朝代·作者）格式，且只能引用资料中真实出现的篇目，不得编造出处；\n"
        "③ 优先引用【⚠ 共享作品】与含『经典』标记的名句；\n"
        "④ 资料不足时，请大胆结合古典诗词学识补充作答，并用『据本地资料』与『学识补充』区分，切勿以资料不足为由拒绝回答；\n"
        "⑤ 像『哪些诗人最爱用某意象』这类问题，据学识给出合理判断并说明理由。\n"
        "⑥ 语气典雅自然、有温度，像一位博学的诗友在对话，而非百科条目；输出纯文本，不要使用 Markdown 符号（**、#、-、列表符号等），可用换行分段。\n"
        "⑦ 引用标注：每条资料前有 [数字] 角标；回答中凡引用某条资料，就在对应句子末尾标注相同的 [数字]，只标注真实引用到的资料，不要臆造不存在的角标。\n\n"
        + "\n".join(parts)
        + f"\n\n【用户问题】{question}"
    )
    return prompt, refs


def _parse_citations(text: str, max_idx: int) -> list[int]:
    """提取回答中出现的合法 [n]/〔n〕 角标（去重、按出现顺序）"""
    import re
    seen = []
    for m in re.findall(r"[\[〔](\d+)[\]〕]", text):
        n = int(m)
        if 1 <= n <= max_idx and n not in seen:
            seen.append(n)
    return seen


def _normalize_brackets(text: str) -> str:
    """把全角 〔n〕 角标统一成半角 [n]，便于解析与前端渲染"""
    return re.sub(r"〔(\d+)〕", r"[\1]", text)


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


def _smalltalk(text: str) -> str | None:
    """轻量寒暄/身份/致谢识别，让助手能自然聊天"""
    t = (text or "").strip().lower()
    if any(w in t for w in ("你好", "您好", "嗨", "哈喽", "hello", "hi", "在吗", "早上好", "下午好", "晚上好")):
        return "你好呀，我是「诗象万千」的灵犀助手。可以问我意象的含义、演变与代表诗句，或让我依格律为你创诗。比如：「月」在古诗里有哪些含义？"
    if any(w in t for w in ("你是谁", "你叫什么", "介绍一下你", "你能做什么", "你会什么", "帮助", "怎么用", "使用说明", "有什么功能")):
        return "我是「诗象万千」灵犀助手，能陪你漫游古诗词意象世界。\n\n你可以问我：\n· 某个意象（如「月」「夕阳」「柳」「雁」）的含义与演变；\n· 哪些诗人最爱用某意象、代表诗句；\n· 多个意象的共现关系；\n· 也可切换到「意象创诗」，让我依格律为你写诗。"
    if any(w in t for w in ("谢谢", "多谢", "感谢", "thanks", "辛苦", "很棒", "真好", "不错")):
        return "不客气～能陪你一起读诗，是我的荣幸。还想探索哪个意象呢？"
    if any(w in t for w in ("再见", "拜拜", "bye", "告辞", "晚安")):
        return "后会有期～愿你「诗象」常伴，下次再一起漫游意象之境。"
    return None


def _resolve_from_history(db: Session, context_msgs: list[dict] | None) -> list[Concept]:
    """从对话历史中还原最近讨论的意象，用于处理'它/这个/这首诗'等指代追问"""
    for m in reversed(context_msgs or []):
        cs = _find_concepts(db, (m.get("content") or "")[:300])
        if cs:
            return cs[:2]
    return []


def _followup_suggestions(db: Session, concepts: list[Concept] | None = None) -> list[str]:
    if concepts:
        n = concepts[0].name
        return [
            f"「{n}」的情感色彩经历了怎样的演变？",
            f"哪些诗人最爱用「{n}」意象？",
            f"和「{n}」经常一起出现的意象有哪些？",
        ]
    sample = [c.name for c in db.query(Concept).limit(3).all()]
    return [f"「{n}」在古诗里有什么含义？" for n in sample] or ["月有哪些含义？", "夕阳为何总与离愁相伴？", "柳和雁分别寄托什么？"]


def ask(db: Session, question: str, context_msgs: list[dict] | None = None) -> dict:
    """context_msgs: [{"role": "user"|"ai", "content": "..."}] 完整对话历史"""
    concepts = _find_concepts(db, question)
    emotions = _find_emotions(question)

    # 指代解析：当前问题未命中意象时，从历史中还原最近讨论的意象
    if not concepts and context_msgs:
        concepts = _resolve_from_history(db, context_msgs)

    mentioned_poems = _find_mentioned_poems(db, question)
    if mentioned_poems and not concepts:
        # 从提及的诗篇反推概念
        for mp in mentioned_poems:
            for c in mp["concepts"]:
                cc = db.get(Concept, c["id"])
                if cc and cc.id not in {x.id for x in concepts}:
                    concepts.append(cc)

    # ==== 语义检索·意象（向量库，先找意象，命中则并入；后段再用其名句）====
    sem = {"concepts": [], "clauses": []}
    try:
        sem = embedding_index.semantic_search(db, question, top_k=6)
    except Exception:
        pass
    existing_cids = {c.id for c in concepts}
    for sc in sem.get("concepts", []):
        cc = db.get(Concept, sc["concept_id"])
        if cc and cc.id not in existing_cids:
            concepts.append(cc)
            existing_cids.add(cc.id)

    if not concepts:
        st = _smalltalk(question)
        if st:
            return {"answer": st, "source": "local",
                    "references": {"concepts": [], "poetries": [], "artworks": []},
                    "suggestions": _followup_suggestions(db)}
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
                cited_titles = set(re.findall(r"《(.+?)》", answer))
                mp_refs = []
                for ct in cited_titles:
                    mp = db.query(Poetry).filter_by(title=ct).first()
                    if mp:
                        mp_refs.append({"poetry_id": mp.id, "title": mp.title, "author": mp.author,
                                        "dynasty": mp.dynasty, "writing_type": mp.writing_type,
                                        "clauses": [], "shared": False})
                return {"answer": answer, "source": "llm_free",
                        "references": {"concepts": [], "poetries": mp_refs[:6], "artworks": []},
                        "suggestions": _followup_suggestions(db)}

        all_c = db.query(Concept).all()
        names = "、".join(f"「{c.name}」" for c in all_c)
        examples = "、".join(f"「{c.name}」在古诗里有什么含义？" for c in all_c[:2])
        return {
            "answer": f"本地意象库收录：{names}。您的问题未命中。例如：{examples}",
            "source": "local",
            "references": {"concepts": [], "poetries": [], "artworks": []},
            "suggestions": _followup_suggestions(db),
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

    # ==== 语义检索·名句（向量库，命中后并入上下文）====
    existing_pids = {p["poetry_id"] for p in poetries}
    sem_by_poetry = {}
    for sc in sem.get("clauses", []):
        pid = sc["poetry_id"]
        if not pid or pid in existing_pids:
            continue
        if pid not in sem_by_poetry:
            sem_by_poetry[pid] = {"poetry_id": pid, "title": sc["title"], "author": sc["author"],
                                  "dynasty": sc["dynasty"], "writing_type": "", "content": "",
                                  "clauses": [], "shared": False, "from_semantic": True}
        sem_by_poetry[pid]["clauses"].append({
            "clause": sc["clause"], "emotion": sc["emotion"], "is_classic": sc["is_classic"],
            "weight": 2, "concept_id": sc["concept_id"], "concept_name": sc["concept_name"],
        })
    if sem_by_poetry:
        poetries = list(sem_by_poetry.values()) + poetries

    if llm.llm_available():
        # 对话历史放入 system 消息——LLM 必须根据历史解析当前问题中的指代（"他"、"这首诗"等）
        system_text = (
            "你是「诗象万千」的博学古典诗词助手，性格儒雅、有温度，像一位随时陪人读诗解诗的诗友。"
            "回答时优先引用本地资料中的篇目并标注《篇名》（朝代·作者）出处；"
            "当资料不足以完整回答时，请自由运用古典诗词学识补充作答，"
            "并用『据本地资料』与『学识补充』加以区分。"
            "切勿因资料缺乏量化数据而拒绝回答——应尽力给出有依据、有分寸的解答，"
            "对无法确证之处如实说明即可。回答宜先结论后展开，典雅自然，"
            "使用纯文本，不用 Markdown 符号（**、#、- 等），可用换行分段。"
        )
        if context_msgs:
            lines = []
            for m in context_msgs[-6:]:
                role = "用户" if m["role"] == "user" else "助手"
                # 去掉历史消息里残留的引用角标，避免 LLM 沿用旧编号
                content = re.sub(r"[\[〔]\d+[\]〕]", "", m["content"][:250])
                lines.append(f"{role}：{content}")
            if lines:
                system_text += (
                    "\n\n=== 对话历史 ===\n"
                    "用户当前提问可能引用历史内容(如 他/这首诗/该作者 等指代词), "
                    "你必须根据以下历史解析指代, 不得当作独立新问题。"
                    "历史中若残留 [数字] 引用编号，是过去对话的编号，与当前资料无关，请忽略，"
                    "只用当前资料中的 [数字] 角标。\n"
                    + "\n".join(lines)
                )
        mentioned_titles = {m["title"] for m in _find_mentioned_poems(db, question)}
        prompt, refs = _build_rag_prompt(concepts, poetries, artworks, question, shared_pids, mentioned_titles)
        msgs = [{"role": "system", "content": system_text},
                {"role": "user", "content": prompt}]
        answer = llm.chat(msgs)
        if answer:
            # 全角〔n〕统一成半角[n]，便于解析与前端渲染
            answer = _normalize_brackets(answer)
            # ── 收集引用：确定性 [n] 角标 + 回答中明确提到的《篇名》/意象名 ──
            cited_idx = _parse_citations(answer, len(refs))
            ref_by_idx = {r["idx"]: r for r in refs}
            cited = [ref_by_idx[i] for i in cited_idx] if cited_idx else []

            def _cite_key(r):
                return (r.get("type"), r.get("poetry_id") or r.get("concept_id") or r.get("artwork_id"))

            seen = {_cite_key(r) for r in cited}

            def _add(r):
                k = _cite_key(r)
                if k in seen:
                    return False
                seen.add(k)
                cited.append(r)
                return True

            # 补扫《篇名》：本地库有、但 LLM 未标角标的，自动补入引用并在文中追加角标
            fallback_poems = []
            for title in re.findall(r"《(.+?)》", answer):
                t = title.strip()
                if not t:
                    continue
                p = next((x for x in poetries if x["title"] == t), None)
                if p:
                    r = {"type": "poetry", "poetry_id": p["poetry_id"], "title": p["title"],
                         "author": p["author"], "dynasty": p["dynasty"],
                         "clause": "；".join(c["clause"] for c in p["clauses"][:2])}
                else:
                    mp = db.query(Poetry).filter_by(title=t).first()
                    if not mp:
                        continue
                    r = {"type": "poetry", "poetry_id": mp.id, "title": mp.title,
                         "author": mp.author, "dynasty": mp.dynasty, "clause": ""}
                if _add(r):
                    fallback_poems.append((t, r))

            # 补扫意象名（仅规范名≥2字，跳过单字/别称噪音）
            for c in concepts:
                if c.name and len(c.name) >= 2 and c.name in answer:
                    _add({"type": "concept", "concept_id": c.id, "name": c.name})

            if not cited:
                cited = refs[:8]

            # 重编号 1..N，并改写回答正文里的角标
            mapping = {}
            for i, r in enumerate(cited, 1):
                old = r.get("idx")
                r["idx"] = i
                if old and old != i:
                    mapping[old] = i
            if mapping:
                answer = re.sub(
                    r"\[(\d+)\]",
                    lambda m: f"[{mapping[int(m.group(1))]}]" if int(m.group(1)) in mapping else m.group(0),
                    answer,
                )
            for title, r in fallback_poems:
                anchor = f"《{title}》"
                answer = answer.replace(anchor, f"{anchor}[{r['idx']}]", 1)

            # 清除无法映射的悬空角标（如 LLM 沿用上一轮的历史编号）
            n_cited = len(cited)
            answer = re.sub(
                r"\[(\d+)\]",
                lambda m: m.group(0) if int(m.group(1)) <= n_cited else "",
                answer,
            )

            poetries_refs, concepts_refs, artworks_refs = [], [], []
            for r in cited:
                if r["type"] == "poetry":
                    poetries_refs.append({"poetry_id": r.get("poetry_id"), "title": r.get("title"),
                                          "author": r.get("author"), "dynasty": r.get("dynasty"),
                                          "clause": r.get("clause", "")})
                elif r["type"] == "concept":
                    concepts_refs.append({"id": r.get("concept_id"), "name": r.get("name")})
                elif r["type"] == "artwork":
                    artworks_refs.append({"id": r.get("artwork_id"), "name": r.get("name"),
                                          "artist": r.get("artist"), "dynasty": r.get("dynasty")})
            if not concepts_refs:
                concepts_refs = [{"id": c.id, "name": c.name} for c in concepts]
            return {
                "answer": answer, "source": "llm",
                "references": {
                    "concepts": concepts_refs,
                    "poetries": poetries_refs,
                    "artworks": artworks_refs,
                    "citations": cited,
                },
                "suggestions": _followup_suggestions(db, concepts),
            }
        # LLM 失败回落
        return {
            "answer": _local_answer(question, concepts, emotions, poetries, shared_pids),
            "source": "local",
            "references": {"concepts": [{"id": c.id, "name": c.name} for c in concepts],
                           "poetries": poetries[:8], "artworks": artworks[:3]},
            "suggestions": _followup_suggestions(db, concepts),
        }

    return {
        "answer": _local_answer(question, concepts, emotions, poetries, shared_pids),
        "source": "local",
        "references": {"concepts": [{"id": c.id, "name": c.name} for c in concepts],
                       "poetries": poetries[:8], "artworks": artworks[:3]},
        "suggestions": _followup_suggestions(db, concepts),
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


# ═══════════════ 意象创诗 ═══════════════
STYLE_SPECS = {
    "五言绝句": {"lines": 4, "chars": 5},
    "七言绝句": {"lines": 4, "chars": 7},
    "五言律诗": {"lines": 8, "chars": 5},
    "七言律诗": {"lines": 8, "chars": 7},
}


def _parse_compose_output(out: str, concepts: list, style: str) -> tuple[str, str]:
    """解析 LLM 输出中的 标题/诗句；失败时兜底提取"""
    title, poem = "", ""
    lines = [l.strip() for l in out.splitlines()]
    poem_started = False
    poem_parts = []
    markers = ("诗文：", "诗文:", "全诗：", "全诗:", "诗：", "诗:")
    for s in lines:
        if not s:
            continue
        if s.startswith(("标题：", "标题:", "题目：", "题目:")):
            title = s.split("：", 1)[-1].split(":", 1)[-1].strip().strip("《》")
            continue
        if s.startswith(markers):
            head = s.split("：", 1)[-1].split(":", 1)[-1].strip()
            if head:
                poem_parts.append(head)
            poem_started = True
            continue
        if poem_started:
            poem_parts.append(s)
    poem = "\n".join(poem_parts)
    if not poem:
        # 兜底：取非标题行的连续文本
        cand = [l for l in lines if l and not l.startswith(("标题", "题目"))]
        poem = "\n".join(cand)
    poem = poem.replace("\\n", "\n").strip("《》 ").strip()
    if not title:
        title = f"咏{'·'.join(concepts[:2])}" if concepts else "无题"
    return title, poem


def _local_compose(concepts: list, style: str, theme: str) -> dict:
    """无 LLM 时的模板创诗兜底：将意象嵌入固定句式，凑足字数"""
    spec = STYLE_SPECS.get(style, STYLE_SPECS["七言绝句"])
    n_chars, n_lines = spec["chars"], spec["lines"]
    name = (concepts[0] if concepts else "月")
    tails = {
        5: ["生清辉", "入梦来", "寄远思", "动客愁", "照无眠"],
        7: ["光照彻古今情", "一片入梦来", "犹照离人衣", "共看应相似", "千里与君同"],
    }
    pool = tails.get(n_chars, tails[7])
    lines = []
    for i in range(n_lines):
        tail = pool[i % len(pool)]
        prefix = "咏" if n_chars - len(name) - len(tail) == 1 else ""
        line = (prefix + name + tail)
        line = line[:n_chars]
        while len(line) < n_chars:
            line += "云山川月夜雪"[len(line) % 6]
        lines.append(line)
    poem = "\n".join(lines)
    note = "未配置大模型，此为模板示例。配置 LLM 后可获得真正依格律创作的诗句。"
    return {"poem": poem, "title": f"咏{name}", "style": style, "source": "local",
            "tones": poem_tones(lines), "note": note}


def compose(db: Session, concepts: list, style: str, theme: str = "") -> dict:
    """意象创诗：输入意象+体裁+情感基调，返回诗作+平仄标注"""
    spec = STYLE_SPECS.get(style) or STYLE_SPECS["七言绝句"]
    style = next((k for k in STYLE_SPECS if STYLE_SPECS[k] == spec), style)

    # 收集意象上下文
    cinfo = []
    for cname in concepts[:5]:
        c = db.query(Concept).filter_by(name=cname).first()
        if c and c.poetic_meaning:
            cinfo.append(f"「{c.name}」：{c.poetic_meaning[:70]}（情感：{c.emotion_tags}）")
        else:
            cinfo.append(f"「{cname}」")
    context = "；".join(cinfo) if cinfo else ""

    if llm.llm_available():
        if theme:
            tones = [t for t in re.split(r"[、，,\s]+", theme) if t]
            if len(tones) > 1:
                theme_line = f"④ 情感基调为「{'、'.join(tones)}」，请将多种情绪融合为统一、含蓄的整体诗境（融情入景、气韵贯通），而非机械罗列各情绪；"
            else:
                theme_line = f"④ 情感基调为「{theme}」，请融情入景；"
        else:
            theme_line = "④ 情感基调由你根据意象、诗体与语境自行把握；"
        prompt = (
            f"请以古典诗词意象「{'、'.join(concepts)}」为题，创作一首{style}。\n"
            f"要求：① 全诗 {spec['lines']} 句，每句 {spec['chars']} 字（不含标点）；"
            f"② 自然融入{'、'.join(concepts)}意象；③ 尽量合乎格律、押韵；"
            f"{theme_line}⑤ 为作品拟一个标题。\n"
            + (f"意象参考：{context}\n" if context else "")
            + "请严格按以下格式输出，不要输出其它内容：\n标题：<标题>\n诗文：<全诗，每句用\\n分隔>"
        )
        out = llm.chat([
            {"role": "system", "content": "你是古典诗词创作名家，精通平仄格律与唐宋意象。仅按用户要求的格式输出。"},
            {"role": "user", "content": prompt},
        ], temperature=0.9)
        if out:
            title, poem = _parse_compose_output(out, concepts, style)
            lines = [l.strip() for l in poem.split("\n") if l.strip()]
            return {"poem": "\n".join(lines), "title": title, "style": style, "source": "llm",
                    "tones": poem_tones(lines), "note": "AI 依格律创作，平仄按现代读音标注，仅供参考。"}

    return _local_compose(concepts, style, theme)
