# -*- coding: utf-8 -*-
"""轻量 RAG 智能助手：本地知识库检索 + 模板生成，可选接入大模型

流程（与方案一致）：
1. 从问题中提取意象关键词（意象名/别称）与情感关键词
2. SQL 检索：意象基础信息 + 关联名句 + 关联意象 + 对应古画
3. 若配置大模型：将检索结果拼装为上下文 Prompt，约束模型仅基于资料回答
   若未配置：本地模板引擎基于同一检索结果生成结构化回答（零幻觉，可离线演示）
4. 返回回答 + 引用来源（诗文/古画/意象）
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
    "怀人": ["怀人", "思念", "怀念", "相思", "怀古伤今", "想念", "悼亡"],
    "孤寂": ["孤寂", "孤独", "寂寞", "孤单", "落寞", "清冷", "独处"],
    "时空永恒": ["永恒", "时空", "宇宙", "时间", "古今", "历史", "哲学", "人生短暂"],
    "怀古": ["怀古", "咏史", "兴亡", "兴废", "古迹", "历史", "六朝"],
    "落寞": ["落寞", "萧瑟", "凄凉", "苍茫", "荒凉", "惆怅"],
    "时光流逝": ["时光", "岁月", "流逝", "迟暮", "黄昏", "年华", "老去"],
    "离愁": ["离愁", "离别", "送别", "分别", "离人", "断肠", "天涯"],
}


def _find_concepts(db: Session, text: str) -> list[Concept]:
    """按意象名与别称匹配问题中提到的意象"""
    found: OrderedDict[int, Concept] = OrderedDict()
    for c in db.query(Concept).all():
        names = [c.name] + [a for a in c.aliases.split(",") if a]
        if any(n and n in text for n in names):
            found[c.id] = c
    return list(found.values())


def _find_emotions(text: str) -> list[str]:
    hits = []
    for tag, words in EMOTION_KEYWORDS.items():
        if any(w in text for w in words):
            hits.append(tag)
    return hits


def _gather_context(db: Session, concepts: list[Concept], emotions: list[str], limit: int = 6):
    """检索意象关联名句（可按情感过滤）与古画"""
    poetries, artworks = [], []
    for c in concepts:
        q = (
            db.query(ConceptPoetryRel, Poetry)
            .join(Poetry, ConceptPoetryRel.poetry_id == Poetry.id)
            .filter(ConceptPoetryRel.concept_id == c.id)
        )
        rels = q.all()
        # 情感过滤优先，其次权重
        if emotions:
            matched = [r for r in rels if r[0].emotion in emotions]
            rels = matched or rels
        rels = sorted(rels, key=lambda r: (r[0].is_classic, r[0].weight), reverse=True)
        for rel, p in rels[:limit]:
            poetries.append({
                "clause": rel.clause, "emotion": rel.emotion,
                "title": p.title, "author": p.author, "dynasty": p.dynasty, "poetry_id": p.id,
            })
        arel = (
            db.query(ConceptArtworkRel, Artwork)
            .join(Artwork, ConceptArtworkRel.artwork_id == Artwork.id)
            .filter(ConceptArtworkRel.concept_id == c.id)
            .order_by(ConceptArtworkRel.weight.desc())
            .limit(3).all()
        )
        for rel, a in arel:
            artworks.append({
                "id": a.id, "name": a.name, "artist": a.artist, "dynasty": a.dynasty,
                "thumb_url": a.thumb_url, "relation_desc": rel.relation_desc,
            })
    return poetries, artworks


def _local_answer(question: str, concepts: list[Concept], emotions: list[str], poetries: list[dict]) -> str:
    parts = []
    for c in concepts:
        emo = "、".join(c.emotion_tags.split(","))
        parts.append(f"「{c.name}」{c.poetic_meaning.split('。')[0]}。其核心情感可归纳为：{emo}。")
    if emotions:
        emo_text = "、".join(emotions)
        matched = [p for p in poetries if p["emotion"] in emotions]
        if matched:
            lines = "\n".join(f"· {p['clause']} —— {p['dynasty']}·{p['author']}《{p['title']}》" for p in matched[:4])
            parts.append(f"就您关注的「{emo_text}」而言，最具代表性的诗句有：\n{lines}")
    else:
        lines = "\n".join(f"· {p['clause']}（{p['emotion']}）—— {p['dynasty']}·{p['author']}《{p['title']}》" for p in poetries[:5])
        parts.append(f"历代经典诗句如：\n{lines}")
    if concepts:
        c0 = concepts[0]
        parts.append(f"演变脉络：{c0.name}意象起源于{c0.origin_dynasty}，鼎盛于{c0.peak_dynasty}。{c0.description.split('。')[0]}。")
    parts.append("（以上回答由本地意象知识库生成，所有引用均可溯源至库中数据。）")
    return "\n\n".join(parts)


def ask(db: Session, question: str) -> dict:
    concepts = _find_concepts(db, question)
    emotions = _find_emotions(question)
    if not concepts:
        all_c = db.query(Concept).all()
        names = "、".join(f"「{c.name}」" for c in all_c)
        examples = "、".join(f"「{c.name}」在古诗里有什么含义？" for c in all_c[:2])
        return {
            "answer": f"抱歉，当前知识库收录的意象为：{names}。您的问题未命中其中任何一个。"
                      f"您可以换个问法，例如：{examples}",
            "source": "local",
            "references": {"concepts": [], "poetries": [], "artworks": []},
        }

    poetries, artworks = _gather_context(db, concepts, emotions)

    # 优先走大模型（上下文严格限定本地检索结果）
    if llm.llm_available():
        ctx_lines = [f"意象「{c.name}」：{c.poetic_meaning} 情感标签：{c.emotion_tags}" for c in concepts]
        ctx_lines += [f"诗句「{p['clause']}」（{p['emotion']}）出自{p['dynasty']}{p['author']}《{p['title']}》" for p in poetries]
        ctx_lines += [f"古画《{a['name']}》（{a['dynasty']}·{a['artist']}）：{a['relation_desc']}" for a in artworks]
        prompt = (
            "你是古诗词意象专家。请仅基于以下资料回答用户问题，不得编造资料之外的诗句；"
            "回答需标注所引诗句的出处，语言典雅简洁，200字以内。\n\n【资料】\n"
            + "\n".join(ctx_lines)
            + f"\n\n【问题】{question}"
        )
        answer = llm.chat([
            {"role": "system", "content": "你是严谨的古典文学助手，只依据给定资料作答。"},
            {"role": "user", "content": prompt},
        ])
        if answer:
            return {"answer": answer, "source": "llm",
                    "references": {"concepts": [{"id": c.id, "name": c.name} for c in concepts],
                                   "poetries": poetries[:6], "artworks": artworks[:3]}}

    return {"answer": _local_answer(question, concepts, emotions, poetries), "source": "local",
            "references": {"concepts": [{"id": c.id, "name": c.name} for c in concepts],
                           "poetries": poetries[:6], "artworks": artworks[:3]}}


# ════════════════════════ 意象创诗 ════════════════════════
# 本地格律模板：每首均为合辙押韵、平仄大律合拍的原创拟作
# 结构：{concept_key: {style: [(title, [lines])]}}
_TEMPLATES = {
    "月": {
        "五言绝句": [
            ("月夜有怀", ["月照江上楼，", "清辉入水流。", "独坐思千里，", "天涯共此秋。"]),
            ("寒山望月", ["明月出寒山，", "孤轮悬夜关。", "乡心何处寄，", "随梦到人间。"]),
            ("清宵吟", ["清宵一轮满，", "桂影落樽前。", "欲问姮娥意，", "相思又一年。"]),
        ],
        "七言绝句": [
            ("江楼望月", ["一轮明月照江楼，", "万里清辉入水流。", "欲问姮娥千古事，", "天涯同是此宵秋。"]),
            ("秋夜寄远", ["桂影婆娑夜色寒，", "清光如水浸雕栏。", "相思不尽凭谁诉，", "散入星河照影单。"]),
            ("海月", ["玉露无声湿桂花，", "冰轮初转海天涯。", "嫦娥应解离人恨，", "故把清辉送到家。"]),
        ],
        "五言律诗": [
            ("望月怀乡", ["明月出沧海，", "清辉满戍楼。", "乡心随雁去，", "客梦绕江流。", "露重蛩声细，", "风寒桂影幽。", "故园千里外，", "同此一轮秋。"]),
        ],
        "七言律诗": [
            ("秋夜望月", ["冰轮初上柳梢头，", "万里清光入小楼。", "桂影斜侵书幌静，", "蛩声暗度竹窗幽。", "天涯共此团圆夜，", "海内同怀离别秋。", "欲问姮娥何所似，", "一江烟水自东流。"]),
        ],
    },
    "夕阳": {
        "五言绝句": [
            ("江上晚晴", ["夕阳江上红，", "落霞明远空。", "独登高处望，", "千古一飞鸿。"]),
            ("关山暮", ["落日照关山，", "孤城暮霭间。", "归鸦穿树急，", "倦客几时还。"]),
            ("寒村暮色", ["暮色起寒烟，", "孤村落照边。", "西风吹不尽，", "离恨满山川。"]),
        ],
        "七言绝句": [
            ("登楼望夕", ["一抹残阳照水红，", "半江落霞半江风。", "凭栏望断天涯路，", "千古兴亡夕照中。"]),
            ("荒台怀古", ["斜阳衰草满荒台，", "画角声中暮色哀。", "多少六朝兴废事，", "都随流水向东来。"]),
            ("晚钟", ["古道西风送晚钟，", "残阳影里客愁浓。", "天涯倦倚阑干处，", "望断乡关一万重。"]),
        ],
        "五言律诗": [
            ("空山落照", ["落日照空山，", "归云度远关。", "鸟衔残色去，", "人立暮烟间。", "古道埋荒草，", "寒城枕碧湾。", "兴亡千古事，", "都付水潺湲。"]),
        ],
        "七言律诗": [
            ("夕阳怀古", ["一抹残阳落照红，", "半江霞影半江风。", "荒台草色迷归鸟，", "古渡钟声入远空。", "多少兴亡千古恨，", "都归渔樵笑谈中。", "独倚危栏无限意，", "夕阳无语下云东。"]),
        ],
    },
    "月+夕阳": {
        "五言绝句": [
            ("江天暮色", ["日落月初生，", "江天一夜清。", "兴亡千古事，", "流水共潮平。"]),
        ],
        "七言绝句": [
            ("江天即景", ["夕阳影里月华生，", "万里江天一夜清。", "今古兴亡多少事，", "都随流水共潮平。"]),
        ],
        "五言律诗": [
            ("夜望", ["日落沧江晚，", "月生沧海秋。", "余霞明远岫，", "清辉满孤舟。", "今古双轮转，", "兴亡一水流。", "凭栏无限意，", "天地共悠悠。"]),
        ],
        "七言律诗": [
            ("江天夜望", ["夕阳西下月初升，", "万里江天澄复清。", "落霞犹染千峰紫，", "新月已窥一棹明。", "今古双轮悬昼夜，", "兴亡一水送功名。", "凭栏试问东流水，", "何似人间万古情。"]),
        ],
    },
}


def compose(db: Session, concept_names: list[str], style: str, theme: str = "") -> dict:
    # 识别意象
    concepts = [c for c in (db.query(Concept).filter(Concept.name.in_(concept_names)).all())]
    names = {c.name for c in concepts}
    key = "+".join(sorted(names, key=concept_names.index)) if names else ""
    if "月" in names and "夕阳" in names:
        key = "月+夕阳"
    elif "月" in names:
        key = "月"
    elif "夕阳" in names:
        key = "夕阳"
    else:
        key = "月"  # 兜底

    # 大模型路径
    if llm.llm_available():
        ctx = "；".join(f"「{c.name}」情感基调：{c.emotion_tags}；经典语境：{c.poetic_meaning[:80]}" for c in concepts)
        prompt = (f"请以{key.replace('+', '与')}为核心意象，创作一首{style}。"
                  f"{'情感基调：' + theme + '。' if theme else ''}要求严格符合{style}格律（句数、字数、押平声韵），"
                  f"语言典雅。参考背景：{ctx}。只输出诗题与诗句，格式：第一行《诗题》，其后每行一句。")
        text = llm.chat([{"role": "user", "content": prompt}], temperature=0.9)
        if text:
            lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
            title = lines[0].strip("《》") if lines else "AI拟作"
            poem_lines = [re.sub(r"[，。；、\s]+$", "", ln) + ("。" if i % 2 else "，") for i, ln in enumerate(lines[1:])]
            return {"title": title, "poem": "\n".join(poem_lines), "style": style, "source": "llm",
                    "tones": poem_tones(poem_lines), "note": "由大模型生成"}

    # 本地模板路径
    bank = _TEMPLATES.get(key)
    if not bank:
        return {
            "title": "", "poem": "", "style": style, "source": "local",
            "tones": [],
            "note": f"本地格律模板暂未收录意象「{key}」（当前仅支持：月、夕阳、月+夕阳）。"
                    "配置 LLM_API_KEY 后可为任意意象自由创作。",
        }
    title, lines = random.choice(bank.get(style, bank["五言绝句"]))
    poem = "\n".join(lines)
    return {
        "title": title, "poem": poem, "style": style, "source": "local",
        "tones": poem_tones(lines),
        "note": "本地格律模板生成（未配置大模型）；配置 LLM_API_KEY 后可切换为大模型自由创作。",
    }
