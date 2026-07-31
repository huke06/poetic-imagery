"""意象模块接口"""
from collections import Counter
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Artwork, Concept, ConceptArtworkRel, ConceptPoetryRel, ConceptRelation, Couplet, DynastyStats, Poetry,
)
from ..schemas import ApiResp
from ..service.share_card import render_exploration_card, render_share_card
from ..utils import llm

router = APIRouter(prefix="/api/concept", tags=["意象"])

# 七大情感主题族（归象用）
EMOTION_THEMES = {
    "思乡怀人": ["思乡", "怀人", "离别", "离愁", "相思"],
    "时光咏怀": ["时光流逝", "怀古", "落寞", "惜春"],
    "孤寂哲思": ["孤寂", "时空永恒", "哲理"],
    "豪迈壮烈": ["豪迈", "壮烈", "激昂", "慷慨"],
    "苍凉悲壮": ["苍凉", "悲壮", "边塞", "厌战"],
    "自然咏物": ["咏物", "山水", "田园", "闲适"],
    "爱情闺怨": ["爱情", "闺怨", "思念", "怨妇"],
}


def _split_tags(c: Concept) -> list[str]:
    return [t for t in c.emotion_tags.split(",") if t]


def _infer_role(clause: str, concept_name: str) -> str:
    """推断意象在诗句中的角色"""
    if not clause or not concept_name:
        return "意象载体"
    if clause.startswith(concept_name):
        return "主语/起兴"
    if clause.endswith(concept_name):
        return "宾语/寄托"
    if "如" + concept_name in clause or "似" + concept_name in clause:
        return "比喻喻体"
    if concept_name + "如" in clause or concept_name + "似" in clause:
        return "比喻本体"
    return "意境烘托"


def _classify_theme(emotion_tags: list[str]) -> str:
    """将意象情感标签归类到七大主题族"""
    scores = {theme: 0 for theme in EMOTION_THEMES}
    for tag in emotion_tags:
        for theme, keywords in EMOTION_THEMES.items():
            if tag in keywords:
                scores[theme] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "自然咏物"


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
    db: Session = Depends(get_db),
):
    """意象列表"""
    q = db.query(Concept)
    if category:
        q = q.filter(Concept.category_main == category)
    if keyword:
        q = q.filter(Concept.name.contains(keyword))
    items = []
    for c in q.order_by(Concept.id).all():
        classic = (
            db.query(ConceptPoetryRel)
            .filter_by(concept_id=c.id, is_classic=1)
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
            "emotion_tags": _split_tags(c), "theme_color": c.theme_color,
            "classic_clause": classic.clause if classic else "",
            "artwork_thumb": thumb[0] if thumb else "",
            "poetry_count": poetry_count,
        })
    return ApiResp(data={"total": len(items), "items": items})


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
    all_concepts = db.query(Concept).all()
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
    concepts = db.query(Concept).all()
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
    all_concepts = db.query(Concept).all()
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
    """意象详情：基础信息 + 朝代统计 + 情感分布 + 对仗词组"""
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
    poetry_count = db.query(func.count(func.distinct(ConceptPoetryRel.poetry_id))).filter_by(concept_id=c.id).scalar()
    artwork_count = db.query(ConceptArtworkRel).filter_by(concept_id=c.id).count()
    return ApiResp(data={
        "id": c.id, "name": c.name,
        "category_main": c.category_main, "category_sub": c.category_sub,
        "aliases": [a for a in c.aliases.split(",") if a],
        "original_meaning": c.original_meaning, "poetic_meaning": c.poetic_meaning,
        "emotion_tags": _split_tags(c), "origin_dynasty": c.origin_dynasty,
        "peak_dynasty": c.peak_dynasty, "description": c.description,
        "theme_color": c.theme_color,
        "dynasty_stats": dynasty_stats,
        "emotion_stats": [{"emotion": k, "count": v} for k, v in emotion_counter.items()],
        "couplets": couplets,
        "poetry_count": poetry_count, "artwork_count": artwork_count,
    })


@router.get("/{concept_id}/poetries")
def concept_poetries(
    concept_id: int,
    dynasty: str = Query("", description="按朝代筛选"),
    emotion: str = Query("", description="按情感筛选"),
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """意象关联名句列表（分页，支持朝代/情感筛选）"""
    if not db.get(Concept, concept_id):
        raise HTTPException(404, "意象不存在")
    q = (
        db.query(ConceptPoetryRel, Poetry)
        .join(Poetry, ConceptPoetryRel.poetry_id == Poetry.id)
        .filter(ConceptPoetryRel.concept_id == concept_id)
    )
    if dynasty:
        q = q.filter(Poetry.dynasty == dynasty)
    if emotion:
        q = q.filter(ConceptPoetryRel.emotion == emotion)
    total = q.count()
    rows = (q.order_by(ConceptPoetryRel.is_classic.desc(), ConceptPoetryRel.weight.desc(), Poetry.id)
             .offset((page - 1) * page_size).limit(page_size).all())
    items = [{
        "rel_id": rel.id, "clause": rel.clause, "emotion": rel.emotion,
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
        "artwork": {"id": a.id, "name": a.name, "artist": a.artist, "dynasty": a.dynasty,
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
        .order_by(ConceptPoetryRel.is_classic.desc(), ConceptPoetryRel.weight.desc())
        .all()
    )
    for rel, p in rels:
        poet_map.setdefault(p.author, []).append({
            "clause": rel.clause,
            "emotion": rel.emotion,
            "is_classic": rel.is_classic,
            "poetry_title": p.title,
            "dynasty": p.dynasty,
        })

    spectrum = []
    for poet, items in poet_map.items():
        best = max(items, key=lambda x: (x["is_classic"], len(x["clause"])))
        emotions = list(dict.fromkeys(i["emotion"] for i in items if i["emotion"]))
        spectrum.append({
            "poet": poet,
            "dynasty": items[0]["dynasty"],
            "verse_count": len(items),
            "representative_verse": best["clause"],
            "poetry_title": best["poetry_title"],
            "emotion_function": "、".join(emotions) if emotions else "待标注",
            "role_in_poem": _infer_role(best["clause"], c.name),
        })

    spectrum.sort(key=lambda x: x["verse_count"], reverse=True)

    return ApiResp(data={
        "concept_id": concept_id,
        "concept_name": c.name,
        "total_poets": len(spectrum),
        "spectrum": spectrum,
    })
