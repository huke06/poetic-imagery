"""意象模块接口"""
from collections import Counter
import json as _json
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Artwork, Concept, ConceptArtworkRel, ConceptPoetryRel, ConceptRelation,
    CooccurrenceStat, Couplet, DynastyOccurrenceStat, DynastyStats, EmotionStat, Poetry,
)
from ..schemas import ApiResp
from ..service.share_card import render_exploration_card, render_share_card
from ..utils import llm
from ..utils.taxonomy import DYNASTY_GROUPS, EMOTION_MAIN_LABELS, dynasty_group_of, emotion_main_of

router = APIRouter(prefix="/api/concept", tags=["意象"])

# 七大情感主题族（归象用）——关键词同时覆盖二级情感标签与一级类别名
EMOTION_THEMES = {
    "思乡怀人": ["思乡", "怀人", "离别", "离愁", "相思", "思念", "送别", "羁旅",
                 "交往离别类", "离别交往类"],
    "时光咏怀": ["时光流逝", "怀古", "落寞", "惜春", "历史文化类", "宴饮欢乐类",
                 "怀古咏史", "历史感怀"],
    "孤寂哲思": ["孤寂", "时空永恒", "哲理", "情感心绪类", "人生感悟类", "超脱境界类",
                 "禅意", "仙道", "超脱", "孤独"],
    "豪迈壮烈": ["豪迈", "壮烈", "激昂", "慷慨", "志向抱负类", "建功立业", "咏物言志",
                 "忧国忧民", "家国情怀"],
    "苍凉悲壮": ["苍凉", "悲壮", "边塞", "厌战", "战争苦难", "边塞苍凉", "民生疾苦"],
    "自然咏物": ["咏物", "山水", "田园", "闲适", "自然山水类", "季节感怀类", "自然赞美",
                 "山水闲适"],
    "爱情闺怨": ["爱情", "闺怨", "怨妇", "相思之情"],
}

# 一级情感类别 → 主题族（关键词未命中时的兜底归类）
PRIMARY_TO_THEME = {
    "自然山水类": "自然咏物", "历史文化类": "时光咏怀", "超脱境界类": "孤寂哲思",
    "人生感悟类": "孤寂哲思", "交往离别类": "思乡怀人", "志向抱负类": "豪迈壮烈",
    "情感心绪类": "孤寂哲思",
}


def _split_tags(c: Concept) -> list[str]:
    return [t for t in c.emotion_tags.split(",") if t]


ROLE_OPTIONS = [
    "起兴",     # 意象领起全句/全篇，兴发感发（《诗经》六义之兴）
    "比喻",     # 以他物喻意象，或以此意象喻他物（修辞学·譬喻）
    "拟人",     # 赋予意象人的情感、行为或意识（修辞学·拟人）
    "用典",     # 化用历史典故或前人诗句中的意象（修辞学·用典）
    "对偶",     # 与另一意象在平行位置形成对举（修辞学·对偶）
    "烘托",     # 营造氛围、渲染意境，非核心语法成分（意境论·烘托）
    "象征",     # 意象作为抽象情感/理念的具象符号（诗学·象征）
]

def _infer_role(clause: str, concept_name: str) -> str:
    """推断意象在诗句中的角色（优先读取缓存，否则规则兜底）"""
    if not clause or not concept_name:
        return "意象载体"
    # 优先用 LLM 缓存的角色
    cached = _find_cached_role(clause, concept_name)
    if cached:
        return cached
    # 规则兜底
    if "如" + concept_name in clause or "似" + concept_name in clause or concept_name + "如" in clause or concept_name + "似" in clause:
        return "比喻"
    if clause.startswith(concept_name):
        return "起兴"
    if "典故" in clause or "犹记" in clause or "曾闻" in clause:
        return "用典"
    return "烘托"


# module-level cache for LLM roles, avoids repeated DB hits in a single request
_role_cache: dict[tuple[str, str], str] = {}

def _find_cached_role(clause: str, concept_name: str) -> str:
    key = (clause, concept_name)
    if key in _role_cache:
        return _role_cache[key]
    # Try from DB (via a quick query — we use a global session helper here)
    # For simplicity, the spectrum endpoint passes the DB session; we look up at call site
    return ""


def analyze_roles_for_concept(db, concept_id: int, batch_size: int = 5) -> int:
    """对某个意象的所有未分析句读，批量调用 LLM 推断角色，返回更新条数"""
    from ..utils.llm import chat, llm_available
    if not llm_available():
        return 0

    rels = db.query(ConceptPoetryRel).filter(
        ConceptPoetryRel.concept_id == concept_id,
        ConceptPoetryRel.role_in_poem == "",
    ).all()
    if not rels:
        return 0

    concept = db.get(Concept, concept_id)
    name = concept.name if concept else ""
    updated = 0

    for i in range(0, len(rels), batch_size):
        batch = rels[i:i + batch_size]
        items = []
        for rel in batch:
            items.append(f'[{rel.id}] "{rel.clause}"')

        prompt = (
            f'意象「{name}」在以下诗句中，请在 7 个用法维度上分别打分（0=不涉及, 1=弱相关, 2=强相关）：\n'
            f'维度：{", ".join(ROLE_OPTIONS)}\n\n'
            + '\n'.join(items)
            + '\n\n请用 JSON 数组回复，每条格式：\n'
            + '{"id": 数字, "role": "主要角色", "scores": {"起兴":0,"比喻":0,"拟人":0,"用典":0,"对偶":0,"烘托":0,"象征":0}}'
        )
        result = chat([
            {"role": "system", "content": "你是一位古典诗词语法分析专家。只回复 JSON 数组。"},
            {"role": "user", "content": prompt},
        ])
        if not result:
            continue

        # 解析 JSON 响应
        try:
            parsed = _json.loads(result.strip().lstrip("```json").rstrip("```"))
            for rel in batch:
                entry = next((p for p in parsed if isinstance(p, dict) and p.get("id") == rel.id), None)
                if not entry:
                    continue
                rel.role_in_poem = entry.get("role", "")
                scores = entry.get("scores", {})
                if isinstance(scores, dict) and scores:
                    rel.usage_keywords = _json.dumps(scores, ensure_ascii=False)
                updated += 1
        except Exception:
            continue

    db.commit()
    return updated


def _classify_theme(emotion_tags: list[str]) -> str:
    """将意象情感标签归类到七大主题族。

    三级兜底：① 关键词精确计分 → ② 一级情感类别映射 → ③ 子串模糊匹配 → 默认自然咏物。
    """
    scores = {theme: 0 for theme in EMOTION_THEMES}
    for tag in emotion_tags:
        for theme, keywords in EMOTION_THEMES.items():
            if tag in keywords:
                scores[theme] += 1
    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best
    # 兜底一：标签本身是一级情感类别（导入数据常见）
    for tag in emotion_tags:
        main = emotion_main_of(tag)
        if main in PRIMARY_TO_THEME:
            return PRIMARY_TO_THEME[main]
    # 兜底二：子串模糊匹配
    for tag in emotion_tags:
        for theme, keywords in EMOTION_THEMES.items():
            if any(k in tag or tag in k for k in keywords):
                return theme
    return "自然咏物"


def _cooccurrence_stats(db: Session, cid_a: int, cid_b: int) -> dict:
    """计算两个意象的共现统计：句内/邻句/全诗 + NPMI"""
    rels_a = {r.poetry_id: r.clause for r in db.query(ConceptPoetryRel).filter_by(concept_id=cid_a).all()}
    rels_b = {r.poetry_id: r.clause for r in db.query(ConceptPoetryRel).filter_by(concept_id=cid_b).all()}
    shared_pids = sorted(set(rels_a) & set(rels_b))
    total = db.query(Poetry).count()
    count_a = len(set(rels_a))
    count_b = len(set(rels_b))
    same_sentence = adj_sentence = 0

    for pid in shared_pids:
        poem = db.get(Poetry, pid)
        if not poem:
            continue
        sentences = [s.strip() for s in re.split(r"[。！？；\n]+", poem.content) if s.strip()]
        pos_a = [i for i, s in enumerate(sentences) if rels_a[pid] in s]
        pos_b = [i for i, s in enumerate(sentences) if rels_b[pid] in s]
        for pa in pos_a:
            for pb in pos_b:
                if pa == pb:
                    same_sentence += 1
                elif abs(pa - pb) == 1:
                    adj_sentence += 1
    shared = len(shared_pids)

    # NPMI
    npmi = 0.0
    if total and count_a and count_b and shared:
        import math
        p_a = count_a / total
        p_b = count_b / total
        p_ab = shared / total
        denom = p_a * p_b
        if denom > 0 and p_ab > 0:
            pmi = math.log(p_ab / denom)
            npmi = max(-1.0, min(1.0, pmi / (-math.log(p_ab))))

    return {"same_sentence": same_sentence, "adjacent_sentence": adj_sentence,
            "same_poem": shared, "npmi": round(npmi, 4)}


# ═══════════════════════════════════════════
# 静态路由（必须在 /{concept_id} 之前）
# ═══════════════════════════════════════════

@router.get("/list")
def concept_list(
    category: str = Query("", description="一级分类筛选"),
    keyword: str = Query("", description="名称关键词"),
    emotion_main: str = Query("", description="一级情感筛选"),
    emotion: str = Query("", description="二级情感筛选"),
    featured: bool = Query(False, description="仅返回首页精选推荐"),
    db: Session = Depends(get_db),
):
    """意象列表（支持分类/关键词/一二级情感筛选，返回情感树供前端渲染）"""
    q = db.query(Concept)
    q = q.filter(Concept.category_sub != "桥接词")  # 桥接词不出现在意象列表
    if featured:
        q = q.filter(Concept.is_featured == True)
    if category:
        q = q.filter(Concept.category_main == category)
    if keyword:
        q = q.filter(Concept.name.contains(keyword))

    # 先聚合全库情感树（一级 → 二级集合），不受当前筛选影响，保证筛选器选项稳定
    emotion_tree: dict[str, set] = {}
    for c in db.query(Concept).filter(Concept.category_sub != "桥接词").all():
        for tag in _split_tags(c):
            if tag in EMOTION_MAIN_LABELS:
                emotion_tree.setdefault(tag, set())  # 一级标签自身作为选项
                continue
            main = emotion_main_of(tag)
            if main:
                emotion_tree.setdefault(main, set()).add(tag)
    emotion_tree_sorted = {
        m: sorted(emotion_tree[m]) for m in EMOTION_MAIN_LABELS if m in emotion_tree
    }

    items = []
    for c in q.order_by(Concept.id).all():
        tags = _split_tags(c)
        mains = [m for m in EMOTION_MAIN_LABELS
                 if any(emotion_main_of(t) == m for t in tags)]
        # 情感筛选（一级命中任一标签即可；二级需精确含该标签）
        if emotion_main and emotion_main not in mains:
            continue
        if emotion and emotion not in tags:
            continue
        classic = (
            db.query(ConceptPoetryRel)
            .filter(ConceptPoetryRel.concept_id == c.id, ConceptPoetryRel.weight >= 2)
            .order_by(ConceptPoetryRel.weight.desc()).first()
        )
        thumb = (
            db.query(Artwork.thumb_url)
            .join(ConceptArtworkRel, ConceptArtworkRel.artwork_id == Artwork.id)
            .filter(ConceptArtworkRel.concept_id == c.id)
            .order_by(ConceptArtworkRel.weight.desc()).first()
        )
        poetry_count = db.query(func.count(func.distinct(ConceptPoetryRel.poetry_id))).filter_by(concept_id=c.id).scalar()
        items.append({
            "id": c.id, "name": c.name,
            "category_main": c.category_main, "category_sub": c.category_sub,
            "aliases": [a for a in c.aliases.split(",") if a],
            "emotion_tags": tags, "emotion_mains": mains, "theme_color": c.theme_color,
            "is_featured": bool(c.is_featured),
            "classic_clause": classic.clause if classic else "",
            "artwork_thumb": thumb[0] if thumb else "",
            "poetry_count": poetry_count,
        })
    return ApiResp(data={"total": len(items), "items": items, "emotion_tree": emotion_tree_sorted})


@router.get("/resolve")
def concept_resolve(
    q: str = Query(..., min_length=1, description="用户输入的搜索词"),
    db: Session = Depends(get_db),
):
    """搜索词归一化：查询别名映射表，返回标准意象。"""
    q = q.strip()

    # 1. 精确匹配 name
    exact = db.query(Concept).filter(Concept.name == q).first()
    if exact:
        return ApiResp(data={
            "found": True, "concept_id": exact.id, "name": exact.name,
            "matched_as": "精确匹配",
        })

    # 2. 模糊匹配 name（包含关系）
    contains = db.query(Concept).filter(Concept.name.contains(q)).all()
    if len(contains) == 1:
        return ApiResp(data={
            "found": True, "concept_id": contains[0].id, "name": contains[0].name,
            "matched_as": "模糊匹配",
        })

    # 3. 匹配 aliases
    all_concepts = db.query(Concept).filter(Concept.category_sub != "桥接词").all()
    for c in all_concepts:
        aliases = [a.strip() for a in (c.aliases or "").split(",") if a.strip()]
        if q in aliases:
            return ApiResp(data={
                "found": True, "concept_id": c.id, "name": c.name,
                "matched_as": f"别名映射（{q} → {c.name}）",
            })
        for a in aliases:
            if q in a or a in q:
                return ApiResp(data={
                    "found": True, "concept_id": c.id, "name": c.name,
                    "matched_as": f"别名模糊映射（{q} ≈ {a} → {c.name}）",
                })

    # 4. 未命中：候选列表
    candidates = []
    for c in all_concepts:
        common = len(set(q) & set(c.name))
        if common > 0:
            candidates.append({"id": c.id, "name": c.name, "score": common})
    candidates.sort(key=lambda x: x["score"], reverse=True)
    candidates = candidates[:8]

    # 5. LLM 推荐
    llm_recommendation = None
    if llm.llm_available():
        try:
            prompt = (
                f"用户搜索了意象词「{q}」，但本地意象库中没有收录。"
                f"本地库收录的意象有：{', '.join(c['name'] for c in candidates[:6]) or '月、夕阳、柳、雁'}。"
                f"请推荐1-3个与「{q}」语义最接近的、在古典诗词中常见的意象词（仅回复意象名，用顿号分隔，不超过20字）。"
            )
            llm_recommendation = llm.chat([
                {"role": "system", "content": "你是古典诗词意象专家。只回复意象名，用顿号分隔。"},
                {"role": "user", "content": prompt},
            ])
            if llm_recommendation:
                llm_recommendation = llm_recommendation.strip()
        except Exception:
            llm_recommendation = None

    return ApiResp(data={
        "found": False, "query": q,
        "candidates": candidates,
        "llm_recommendation": llm_recommendation,
        "hint": f"未找到「{q}」相关意象",
    })


@router.get("/panorama")
def concept_panorama(db: Session = Depends(get_db)):
    """意象全景图谱：按七大情感主题族组织所有意象。"""
    concepts = db.query(Concept).filter(Concept.category_sub != "桥接词").all()
    themes_map: dict[str, list] = {}

    for c in concepts:
        tags = [t for t in c.emotion_tags.split(",") if t]
        theme = _classify_theme(tags)
        themes_map.setdefault(theme, []).append({
            "id": c.id,
            "name": c.name,
            "emotion_tags": tags,
            "theme_color": c.theme_color,
            "category_main": c.category_main,
            "poetic_meaning": c.poetic_meaning[:80] if c.poetic_meaning else "",
            "poetry_count": db.query(func.count(func.distinct(ConceptPoetryRel.poetry_id)))
                              .filter_by(concept_id=c.id).scalar() or 0,
        })

    result = []
    for theme, keywords in EMOTION_THEMES.items():
        members = themes_map.get(theme, [])
        members.sort(key=lambda x: x["poetry_count"], reverse=True)
        result.append({
            "theme": theme,
            "keywords": keywords,
            "count": len(members),
            "members": members,
        })

    return ApiResp(data={"themes": result, "total_concepts": len(concepts)})


@router.get("/recommend-similar")
def recommend_similar(
    q: str = Query(..., min_length=1, description="未命中的搜索词"),
    db: Session = Depends(get_db),
):
    """当搜索词在库中不存在时，调用 LLM 推荐相近意象"""
    all_concepts = db.query(Concept).filter(Concept.category_sub != "桥接词").all()
    names = [c.name for c in all_concepts]

    if not llm.llm_available():
        similar = []
        for name in names:
            common = len(set(q) & set(name))
            if common > 0:
                similar.append({"name": name, "score": common})
        similar.sort(key=lambda x: x["score"], reverse=True)
        return ApiResp(data={"recommendations": similar[:5], "source": "local"})

    prompt = (
        f"用户想查询意象「{q}」，但本地库中只有这些意象：{'、'.join(names)}。"
        f"请从库中推荐1-3个与「{q}」语义最接近的意象（仅回复意象名，用顿号分隔，不超过20字）。"
    )
    try:
        text = llm.chat([
            {"role": "system", "content": "你是古典诗词意象专家。仅回复意象名，用顿号分隔。"},
            {"role": "user", "content": prompt},
        ])
        if text:
            recs = [r.strip() for r in re.split(r"[、，,]", text.strip()) if r.strip()]
            valid = [{"name": r, "in_library": r in names} for r in recs if r in names]
            return ApiResp(data={"recommendations": valid[:5], "source": "llm"})
    except Exception:
        pass
    return ApiResp(data={"recommendations": [], "source": "error"})


# ═══════════════════════════════════════════
# 参数化路由（/{concept_id} 及子路由）
# ═══════════════════════════════════════════

@router.get("/{concept_id}")
def concept_detail(concept_id: int, db: Session = Depends(get_db)):
    """意象详情：基础信息 + 朝代统计 + 情感分布 + 对仗词组 + v3 聚合统计"""
    c = db.get(Concept, concept_id)
    if not c:
        raise HTTPException(404, "意象不存在")
    dynasty_stats = [
        {"dynasty": s.dynasty, "count": s.count}
        for s in db.query(DynastyStats).filter_by(concept_id=c.id).all()
    ]
    emotion_counter = Counter(
        r.emotion for r in db.query(ConceptPoetryRel).filter_by(concept_id=c.id).all() if r.emotion
    )
    couplets = [
        {"word_a": cp.word_a, "word_b": cp.word_b, "verse": cp.verse, "source": cp.source}
        for cp in db.query(Couplet).filter_by(concept_id=c.id).all()
    ]

    # ── v3：情感标签占比统计（环形饼图数据源） ──
    aliases = [a for a in c.aliases.split(",") if a]
    word_variants = [c.name] + aliases
    emo_rows = db.query(EmotionStat).filter(EmotionStat.word.in_(word_variants)).all()
    # 多词合并：同一二级标签取占比最大者
    merged_emo: dict[str, dict] = {}
    for r in emo_rows:
        cur = merged_emo.get(r.emotion)
        if not cur or r.ratio > cur["ratio"]:
            merged_emo[r.emotion] = {"emotion": r.emotion, "category": r.category,
                                     "count": r.count, "ratio": r.ratio}
    emotion_tag_stats = sorted(merged_emo.values(), key=lambda x: x["ratio"], reverse=True)

    # ── v3：朝代出现频次统计（演变脉络数据源，九大朝代段） ──
    dyn_rows = db.query(DynastyOccurrenceStat).filter(DynastyOccurrenceStat.word.in_(word_variants)).all()
    merged_dyn: dict[str, int] = {}
    for r in dyn_rows:
        merged_dyn[r.dynasty] = max(merged_dyn.get(r.dynasty, 0), r.count)
    dynasty_occurrence = [{"dynasty": g, "count": merged_dyn.get(g, 0)} for g in DYNASTY_GROUPS]

    # ── v3：本意象名句涉及的一级情感标签 ──
    mains = sorted({r.emotion_main for r in db.query(ConceptPoetryRel)
                    .filter_by(concept_id=c.id).all() if r.emotion_main},
                   key=lambda m: EMOTION_MAIN_LABELS.index(m) if m in EMOTION_MAIN_LABELS else 99)

    # ── v3：本意象名句涉及的原始朝代（去重，用于筛选下拉） ──
    raw_dynasties_raw = {p.dynasty for p in
        db.query(Poetry).join(ConceptPoetryRel, ConceptPoetryRel.poetry_id == Poetry.id)
        .filter(ConceptPoetryRel.concept_id == c.id).all() if p.dynasty}
    # 按时序排列：先按九大段位置，段内按名称
    _GROUP_POS = {g: i for i, g in enumerate(DYNASTY_GROUPS)}
    raw_dynasties = sorted(raw_dynasties_raw,
        key=lambda d: (_GROUP_POS.get(dynasty_group_of(d), 99), d))

    poetry_count = db.query(func.count(func.distinct(ConceptPoetryRel.poetry_id))).filter_by(concept_id=c.id).scalar()
    artwork_count = db.query(ConceptArtworkRel).filter_by(concept_id=c.id).count()
    return ApiResp(data={
        "id": c.id, "name": c.name,
        "category_main": c.category_main, "category_sub": c.category_sub,
        "aliases": aliases,
        "original_meaning": c.original_meaning, "poetic_meaning": c.poetic_meaning,
        "emotion_tags": _split_tags(c), "origin_dynasty": c.origin_dynasty,
        "peak_dynasty": c.peak_dynasty, "description": c.description,
        "theme_color": c.theme_color,
        "dynasty_stats": dynasty_stats,
        "emotion_stats": [{"emotion": k, "count": v} for k, v in emotion_counter.items()],
        "emotion_tag_stats": emotion_tag_stats,
        "dynasty_occurrence": dynasty_occurrence,
        "poetry_dynasties": raw_dynasties,
        "emotion_mains": mains,
        "couplets": couplets,
        "poetry_count": poetry_count, "artwork_count": artwork_count,
    })


@router.get("/{concept_id}/poetries")
def concept_poetries(
    concept_id: int,
    dynasty: str = Query("", description="按朝代筛选"),
    emotion: str = Query("", description="按二级情感标签筛选"),
    emotion_main: str = Query("", description="按一级情感标签筛选"),
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """意象关联名句列表（分页，支持朝代/二级情感/一级情感筛选）"""
    if not db.get(Concept, concept_id):
        raise HTTPException(404, "意象不存在")
    q = (
        db.query(ConceptPoetryRel, Poetry)
        .join(Poetry, ConceptPoetryRel.poetry_id == Poetry.id)
        .filter(ConceptPoetryRel.concept_id == concept_id)
    )
    if dynasty:
        from ..utils.taxonomy import dynasty_group_of
        if dynasty in DYNASTY_GROUPS:
            # 归并朝代段：匹配所有归属于该段的细粒度朝代
            matches = set()
            for p in db.query(Poetry.dynasty).filter(Poetry.id.in_(
                db.query(ConceptPoetryRel.poetry_id).filter(ConceptPoetryRel.concept_id == concept_id)
            )).all():
                if dynasty_group_of(p.dynasty) == dynasty:
                    matches.add(p.dynasty)
            if matches:
                q = q.filter(Poetry.dynasty.in_(matches))
            else:
                q = q.filter(Poetry.dynasty == dynasty)
        else:
            q = q.filter(Poetry.dynasty == dynasty)
    if emotion:
        q = q.filter(ConceptPoetryRel.emotion == emotion)
    if emotion_main:
        q = q.filter(ConceptPoetryRel.emotion_main == emotion_main)
    total = q.count()
    rows = (q.order_by(ConceptPoetryRel.weight.desc(), Poetry.id)
             .offset((page - 1) * page_size).limit(page_size).all())
    items = [{
        "rel_id": rel.id, "clause": rel.clause, "emotion": rel.emotion,
        "emotion_main": rel.emotion_main or emotion_main_of(rel.emotion),
        "is_classic": rel.is_classic, "weight": rel.weight,
        "poetry": {"id": p.id, "title": p.title, "author": p.author, "dynasty": p.dynasty, "writing_type": p.writing_type},
    } for rel, p in rows]
    return ApiResp(data={"total": total, "page": page, "page_size": page_size, "items": items})


@router.get("/{concept_id}/artworks")
def concept_artworks(concept_id: int, db: Session = Depends(get_db)):
    """意象关联古画列表"""
    if not db.get(Concept, concept_id):
        raise HTTPException(404, "意象不存在")
    rows = (
        db.query(ConceptArtworkRel, Artwork)
        .join(Artwork, ConceptArtworkRel.artwork_id == Artwork.id)
        .filter(ConceptArtworkRel.concept_id == concept_id)
        .order_by(ConceptArtworkRel.weight.desc()).all()
    )
    return ApiResp(data=[{
        "rel_id": rel.id, "relation_desc": rel.relation_desc,
        "artwork": {"id": a.id, "name": a.name, "artist": a.artist,
                    "dynasty": a.dynasty_period or a.dynasty_main,
                    "dynasty_main": a.dynasty_main,
                    "image_url": a.image_url, "thumb_url": a.thumb_url},
    } for rel, a in rows])


@router.get("/{concept_id}/relations")
def concept_relations(concept_id: int, db: Session = Depends(get_db)):
    """意象关联网络（v2：含共现统计与 NPMI 连线权重）"""
    c = db.get(Concept, concept_id)
    if not c:
        raise HTTPException(404, "意象不存在")
    edges = (
        db.query(ConceptRelation)
        .filter((ConceptRelation.from_concept_id == concept_id) | (ConceptRelation.to_concept_id == concept_id))
        .all()
    )
    node_ids = {concept_id}
    for e in edges:
        node_ids.update([e.from_concept_id, e.to_concept_id])

    # v2 桥接扩展：包含关系 → 拉取桥接词的共现边（不含包含边自身）
    bridge_ids = {e.to_concept_id for e in edges if e.relation_type == "包含"}
    if bridge_ids:
        bridge_edges = db.query(ConceptRelation).filter(
            ConceptRelation.relation_type == "共现",
            (ConceptRelation.from_concept_id.in_(bridge_ids)) | (ConceptRelation.to_concept_id.in_(bridge_ids))
        ).all()
        for be in bridge_edges:
            node_ids.update([be.from_concept_id, be.to_concept_id])
        edges = list(edges) + bridge_edges

    # 自动共现推导
    my_poetry_ids = {r.poetry_id for r in db.query(ConceptPoetryRel).filter_by(concept_id=concept_id).all()}
    cooccur: dict[int, list[str]] = {}
    if my_poetry_ids:
        for r in (db.query(ConceptPoetryRel).filter(ConceptPoetryRel.poetry_id.in_(my_poetry_ids),
                                                     ConceptPoetryRel.concept_id != concept_id).all()):
            p = db.get(Poetry, r.poetry_id)
            if p:
                cooccur.setdefault(r.concept_id, [])
                if p.title not in cooccur[r.concept_id]:
                    cooccur[r.concept_id].append(p.title)
    node_ids.update(cooccur.keys())

    concepts = {x.id: x for x in db.query(Concept).filter(Concept.id.in_(node_ids)).all()}
    nodes = [{"id": x.id, "name": x.name, "theme_color": x.theme_color,
              "category_main": x.category_main, "category_sub": x.category_sub} for x in concepts.values()]

    manual_pairs = {frozenset((e.from_concept_id, e.to_concept_id)) for e in edges}
    edge_items = []
    for e in edges:
        stats = _cooccurrence_stats(db, e.from_concept_id, e.to_concept_id)
        edge_items.append({
            "id": e.id, "from_id": e.from_concept_id, "to_id": e.to_concept_id,
            "from_name": concepts[e.from_concept_id].name, "to_name": concepts[e.to_concept_id].name,
            "relation_type": e.relation_type, "description": e.description, "auto": False,
            "cooccurrence": stats,
        })
    for other_id, titles in cooccur.items():
        if other_id not in concepts:
            continue
        stats = _cooccurrence_stats(db, concept_id, other_id)
        joined = "、".join(f"《{t}》" for t in titles[:4])
        desc = f"共现于 {joined}{' 等' if len(titles) > 4 else ''}（{len(titles)} 篇）"
        if frozenset((concept_id, other_id)) in manual_pairs:
            for item in edge_items:
                if frozenset((item["from_id"], item["to_id"])) == frozenset((concept_id, other_id)):
                    item["cooccurrence"] = stats
                    break
        else:
            edge_items.append({
                "id": 0, "from_id": concept_id, "to_id": other_id,
                "from_name": concepts[concept_id].name, "to_name": concepts[other_id].name,
                "relation_type": "共现", "description": desc, "auto": True, "cooccurrence": stats,
            })
    return ApiResp(data={"nodes": nodes, "edges": edge_items})


@router.get("/{concept_id}/cooccurrence")
def concept_cooccurrence(concept_id: int, limit: int = Query(24, ge=1, le=60),
                         db: Session = Depends(get_db)):
    """共现分析知识图谱（v3）：探索意象居中，共现意象环绕连线。

    线形规则：粗细=NPMI（归一化[-1,1]映射）；线型=共现类型（实线句内/虚线跨句/点线全诗）；
    透明度=diaphaneity（0.2 为最低值）。
    数据源：cooccurrence_stat 表（CSV 导入的分析结果），库内人工关联补充。
    """
    c = db.get(Concept, concept_id)
    if not c:
        raise HTTPException(404, "意象不存在")

    aliases = [a for a in c.aliases.split(",") if a]
    word_variants = [c.name] + aliases

    # ── 收集共现边（词对级统计表） ──
    edges_map: dict[str, dict] = {}
    stat_rows = db.query(CooccurrenceStat).filter(
        or_(CooccurrenceStat.word_a.in_(word_variants),
            CooccurrenceStat.word_b.in_(word_variants))).all()
    for r in stat_rows:
        other = r.word_b if r.word_a in word_variants else r.word_a
        if other == c.name or other in aliases:
            continue
        prev = edges_map.get(other)
        # 同一共现词多条记录时保留 NPMI 更高者
        if prev and prev["npmi"] >= r.npmi:
            continue
        edges_map[other] = {
            "other": other, "npmi": r.npmi, "type": r.cooccurrence_type,
            "diaphaneity": r.diaphaneity, "verse": r.verse, "description": r.description,
            "poem_title": r.poem_title or "", "poet": r.poet or "", "dynasty": r.dynasty or "",
            "same_sentence": r.same_sentence, "adjacent_sentence": r.adjacent_sentence,
            "same_poem": r.same_poem, "source": "stat",
        }

    # ── 库内人工/同步关联补充（concept_relation） ──
    concept_ids = {c.id}
    rel_rows = db.query(ConceptRelation).filter(
        or_(ConceptRelation.from_concept_id == c.id,
            ConceptRelation.to_concept_id == c.id)).all()
    id2name = {}
    for e in rel_rows:
        other_id = e.to_concept_id if e.from_concept_id == c.id else e.from_concept_id
        concept_ids.add(other_id)
    for cc in db.query(Concept).filter(Concept.id.in_(concept_ids)).all():
        id2name[cc.id] = cc
    for e in rel_rows:
        other_id = e.to_concept_id if e.from_concept_id == c.id else e.from_concept_id
        other_concept = id2name.get(other_id)
        if not other_concept or other_concept.id == c.id:
            continue
        other = other_concept.name
        if other in edges_map and edges_map[other]["npmi"] >= e.npmi:
            continue
        edges_map[other] = {
            "other": other, "npmi": e.npmi, "type": e.cooccurrence_type,
            "diaphaneity": e.diaphaneity, "verse": e.verse, "description": e.description,
            "poem_title": e.poem_title or "", "poet": e.poet or "", "dynasty": e.dynasty or "",
            "same_sentence": e.same_sentence, "adjacent_sentence": e.adjacent_sentence,
            "same_poem": e.same_poem, "source": "relation", "concept_id": other_id,
        }

    # ── v2 桥接扩展：拉取包含关系 → 桥接词的共现边 ──
    bridge_rels = db.query(ConceptRelation).filter_by(from_concept_id=c.id, relation_type="包含").all()
    bridge_concepts = {br.to_concept_id: db.get(Concept, br.to_concept_id) for br in bridge_rels}
    for br in bridge_rels:
        br_concept = bridge_concepts.get(br.to_concept_id)
        if not br_concept: continue
        bridge_name = br_concept.name
        # 桥接词自身的共现边
        br_cooc = db.query(CooccurrenceStat).filter(
            or_(CooccurrenceStat.word_a == bridge_name,
                CooccurrenceStat.word_b == bridge_name)
        ).all()
        for bc in br_cooc:
            other = bc.word_b if bc.word_a == bridge_name else bc.word_a
            if other in edges_map:
                # 已有直接边时，改为桥接链路（优先级更高）
                edges_map[other]["source"] = "bridge"
                edges_map[other]["bridge_word"] = bridge_name
                edges_map[other]["bridge_id"] = br.to_concept_id
                if not edges_map[other].get("verse") and bc.verse: edges_map[other]["verse"] = bc.verse
                if not edges_map[other].get("description") and bc.description: edges_map[other]["description"] = bc.description
                for f in ("poem_title", "poet", "dynasty"):
                    if not edges_map[other].get(f) and getattr(bc, f, ""): edges_map[other][f] = getattr(bc, f, "")
                continue
            # 从 ConceptRelation 补全人工标注的 verse/description
            other_c = db.query(Concept).filter_by(name=other).first()
            if other_c and (not bc.verse or not bc.description):
                br_rels = db.query(ConceptRelation).filter_by(
                    from_concept_id=br.to_concept_id, to_concept_id=other_c.id
                ).all()
                for br_rel in br_rels:
                    if not bc.verse and br_rel.verse: bc.verse = br_rel.verse
                    if not bc.description and br_rel.description: bc.description = br_rel.description

            edges_map[other] = {
                "other": other, "npmi": bc.npmi, "type": bc.cooccurrence_type,
                "diaphaneity": bc.diaphaneity, "verse": bc.verse, "description": bc.description,
                "poem_title": getattr(bc, "poem_title", ""), "poet": getattr(bc, "poet", ""), "dynasty": getattr(bc, "dynasty", ""),
                "same_sentence": bc.same_sentence, "adjacent_sentence": bc.adjacent_sentence,
                "same_poem": bc.same_poem, "source": "bridge",
                "bridge_word": bridge_name, "bridge_id": br.to_concept_id,
            }
    # 桥接词也加入 nodes（覆盖 ConceptRelation 可能产生的空 type）
    for br in bridge_rels:
        br_concept = bridge_concepts.get(br.to_concept_id)
        if br_concept:
            edges_map[br_concept.name] = {
                "other": br_concept.name, "npmi": 0, "type": "包含",
                "diaphaneity": 0.3, "verse": "", "description": "桥接词：" + (br.description or ""),
                "same_sentence": 0, "adjacent_sentence": 0, "same_poem": 0,
                "source": "bridge_node", "bridge_id": br_concept.id, "concept_id": br_concept.id,
            }

    # ── 排序取 top N，构建节点 ──
    edges = sorted(edges_map.values(), key=lambda x: (x["npmi"], x["same_poem"]), reverse=True)[:limit]
    other_names = [e["other"] for e in edges]
    name2concept = {}
    for cc in db.query(Concept).filter(Concept.name.in_(other_names)).all():
        name2concept[cc.name] = cc

    nodes = [{
        "id": f"c{c.id}", "name": c.name, "center": True,
        "concept_id": c.id, "theme_color": c.theme_color,
    }]
    for e in edges:
        oc = name2concept.get(e["other"])
        e["concept_id"] = oc.id if oc else None
        nodes.append({
            "id": f"n{e['other']}", "name": e["other"], "center": False,
            "concept_id": oc.id if oc else None,
            "is_bridge": (oc.category_sub == "桥接词") if oc else False,
            "theme_color": oc.theme_color if oc else "#8A6D3B",
        })

    edge_items = []
    for e in edges:
        src_id = f"n{e['bridge_word']}" if e.get("source") == "bridge" and e.get("bridge_word") else f"c{c.id}"
        tgt_id = f"n{e['other']}"
        rel_type = "包含" if e.get("type") == "包含" else "共现"
        edge_items.append({
        "source": src_id, "target": tgt_id,
        "relation_type": rel_type,
        "name": e["other"], "npmi": e["npmi"], "type": e["type"],
        "diaphaneity": max(0.2, min(1.0, e["diaphaneity"] or 0.2)),
        "verse": e["verse"], "description": e["description"],
        "same_sentence": e["same_sentence"], "adjacent_sentence": e["adjacent_sentence"],
        "same_poem": e["same_poem"], "concept_id": e.get("concept_id"),
        "poem_title": e.get("poem_title", ""), "poet": e.get("poet", ""), "dynasty": e.get("dynasty", ""),
    })

    return ApiResp(data={
        "concept_id": c.id, "concept_name": c.name,
        "nodes": nodes, "edges": edge_items,
    })


@router.get("/{concept_id}/usage-summary")
def concept_usage_summary(concept_id: int, refresh: bool = Query(False), db: Session = Depends(get_db)):
    """AI 用法谱系总结：DB 缓存优先 → LLM 生成 → 回写缓存"""
    c = db.get(Concept, concept_id)
    if not c:
        raise HTTPException(404, "意象不存在")
    if c.usage_summary and not refresh:
        return ApiResp(data={"source": "cache", "text": c.usage_summary})

    # 组装上下文：诗人用法 + 情感功能统计
    spectrum = _build_spectrum(db, c)
    emo_stats = db.query(EmotionStat).filter(EmotionStat.word == c.name).order_by(
        EmotionStat.ratio.desc()).limit(6).all()

    if llm.llm_available():
        poet_desc = "；".join(
            f"{s['poet']}（{s['dynasty']}）以「{s['representative_verse']}」寄{ s['emotion_function']}"
            for s in spectrum[:6]) or "暂无具体诗人用例"
        emo_desc = "、".join(f"{e.emotion}({e.ratio:.1f}%)" for e in emo_stats) or "、".join(_split_tags(c))
        prompt = (
            f"请为古典诗词意象「{c.name}」撰写一段 120-180 字的用法谱系总结。\n"
            f"该意象的核心情感功能占比：{emo_desc}。\n"
            f"历代诗人用法：{poet_desc}。\n"
            f"要求：概括该意象在不同诗人笔下的主要情感功能与风格差异，点明其用法流变，语言典雅凝练，直接成文。"
        )
        result = llm.chat([
            {"role": "system", "content": "你是古典诗词意象研究专家，撰写凝练典雅的用法谱系总结。"},
            {"role": "user", "content": prompt},
        ], temperature=0.5)
        if result:
            c.usage_summary = result.strip()
            db.commit()
            return ApiResp(data={"source": "llm", "text": c.usage_summary})

    fallback = (f"「{c.name}」意象在历代诗人笔下承载了丰富的情感意蕴，"
                f"其核心情感功能集中于{ '、'.join(_split_tags(c)) or '山水寄情' }，"
                f"或借景抒怀，或托物言志，随时代流变而意蕴层叠，构成了一条绵延的用法谱系。")
    return ApiResp(data={"source": "local", "text": c.usage_summary or fallback,
                         "note": "配置大模型后可生成更精准的 AI 总结"})


def _build_spectrum(db: Session, c: Concept) -> list[dict]:
    """复用用法谱系逻辑（供 AI 总结取数）"""
    poet_map: dict[str, list] = {}
    rels = (
        db.query(ConceptPoetryRel, Poetry)
        .join(Poetry, ConceptPoetryRel.poetry_id == Poetry.id)
        .filter(ConceptPoetryRel.concept_id == c.id)
        .order_by(ConceptPoetryRel.weight.desc())
        .all()
    )
    for rel, p in rels:
        poet_map.setdefault(p.author, []).append({
            "clause": rel.clause, "emotion": rel.emotion,
            "is_classic": rel.is_classic, "poetry_title": p.title, "dynasty": p.dynasty,
        })
    spectrum = []
    for poet, items in poet_map.items():
        best = max(items, key=lambda x: (x.get("weight", 0), len(x["clause"])))
        emotions = list(dict.fromkeys(i["emotion"] for i in items if i["emotion"]))
        spectrum.append({
            "poet": poet, "dynasty": items[0]["dynasty"],
            "verse_count": len(items), "representative_verse": best["clause"],
            "emotion_function": "、".join(emotions) if emotions else "待标注",
        })
    spectrum.sort(key=lambda x: x["verse_count"], reverse=True)
    return spectrum


@router.get("/{concept_id}/share-card")
def concept_share_card(concept_id: int, db: Session = Depends(get_db)):
    """生成意象分享卡片（SVG 图片，可直接保存/分享）"""
    c = db.get(Concept, concept_id)
    if not c:
        raise HTTPException(404, "意象不存在")
    classic = (
        db.query(ConceptPoetryRel, Poetry)
        .join(Poetry, ConceptPoetryRel.poetry_id == Poetry.id)
        .filter(ConceptPoetryRel.concept_id == c.id, ConceptPoetryRel.is_classic == 1)
        .order_by(ConceptPoetryRel.weight.desc()).first()
    )
    poetry_count = db.query(func.count(func.distinct(ConceptPoetryRel.poetry_id))).filter_by(concept_id=c.id).scalar() or 0
    artwork_count = db.query(ConceptArtworkRel).filter_by(concept_id=c.id).count()
    svg = render_share_card(c, classic[0].clause if classic else "", classic[1] if classic else None, poetry_count, artwork_count)
    return Response(content=svg, media_type="image/svg+xml")


@router.post("/exploration-card")
def exploration_share_card(payload: dict, db: Session = Depends(get_db)):
    """生成「我的意象地图」分享卡片"""
    explored = payload.get("explored", [])
    report = payload.get("report", "")
    theme_count = payload.get("theme_count", 0)
    svg = render_exploration_card(explored, report, theme_count)
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/{concept_id}/usage-spectrum")
def concept_usage_spectrum(concept_id: int, db: Session = Depends(get_db)):
    """意象用法谱系：同一意象在不同诗人笔下的用法差异。"""
    c = db.get(Concept, concept_id)
    if not c:
        raise HTTPException(404, "意象不存在")

    poet_map: dict[str, list] = {}
    rels = (
        db.query(ConceptPoetryRel, Poetry)
        .join(Poetry, ConceptPoetryRel.poetry_id == Poetry.id)
        .filter(ConceptPoetryRel.concept_id == concept_id)
        .order_by(ConceptPoetryRel.weight.desc())
        .all()
    )
    for rel, p in rels:
        poet_map.setdefault(p.author, []).append({
            "clause": rel.clause,
            "emotion": rel.emotion,
            "is_classic": rel.is_classic,
            "poetry_title": p.title,
            "dynasty": p.dynasty,
            "role_in_poem": rel.role_in_poem,
            "usage_scores": rel.usage_keywords,  # JSON: {"起兴":2,"比喻":1,...}
        })

    spectrum = []
    for poet, items in poet_map.items():
        best = max(items, key=lambda x: (x.get("weight", 0), len(x["clause"])))
        emotions = list(dict.fromkeys(i["emotion"] for i in items if i["emotion"]))
        # 聚合该诗人所有诗句的评分
        agg_scores = {}
        for it in items:
            raw = it.get("usage_scores", "")
            if raw:
                try:
                    s = _json.loads(raw)
                    for k, v in s.items():
                        agg_scores[k] = (agg_scores.get(k, 0) + v)
                except Exception:
                    pass
        spectrum.append({
            "poet": poet,
            "dynasty": items[0]["dynasty"],
            "verse_count": len(items),
            "representative_verse": best["clause"],
            "poetry_title": best["poetry_title"],
            "emotion_function": "、".join(emotions) if emotions else "待标注",
            "role_in_poem": best.get("role_in_poem") or _infer_role(best["clause"], c.name),
            "usage_scores": agg_scores,
        })

    spectrum.sort(key=lambda x: x["verse_count"], reverse=True)

    return ApiResp(data={
        "concept_id": concept_id,
        "concept_name": c.name,
        "total_poets": len(spectrum),
        "spectrum": spectrum,
    })
