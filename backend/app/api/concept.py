"""意象模块接口"""
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Artwork, Concept, ConceptArtworkRel, ConceptPoetryRel, ConceptRelation, Couplet, DynastyStats, Poetry,
)
from ..schemas import ApiResp
from ..service.share_card import render_share_card

router = APIRouter(prefix="/api/concept", tags=["意象"])


def _split_tags(c: Concept) -> list[str]:
    return [t for t in c.emotion_tags.split(",") if t]


@router.get("/list")
def concept_list(
    category: str = Query("", description="分类筛选"),
    keyword: str = Query("", description="名称关键词"),
    db: Session = Depends(get_db),
):
    """意象列表（卡片数据：名称/标签/代表名句/古画缩略图/关联诗数）"""
    q = db.query(Concept)
    if category:
        q = q.filter(Concept.category == category)
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
            "id": c.id, "name": c.name, "category": c.category,
            "emotion_tags": _split_tags(c), "theme_color": c.theme_color,
            "classic_clause": classic.clause if classic else "",
            "artwork_thumb": thumb[0] if thumb else "",
            "poetry_count": poetry_count,
        })
    return ApiResp(data={"total": len(items), "items": items})


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
        "id": c.id, "name": c.name, "category": c.category,
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
    """意象关联网络（力导向图节点与边）

    边分两类：
    - 人工标注边（concept_relation 表：对仗/情感同源/演变衍生等学理关系）
    - 自动共现边：两意象被关联到同一首诗，由数据实时推导，附共现作品清单
    """
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

    # ── 自动共现推导：本意象的每首诗，还被哪些意象关联 ──
    my_poetry_ids = {r.poetry_id for r in db.query(ConceptPoetryRel).filter_by(concept_id=concept_id).all()}
    cooccur: dict[int, list[str]] = {}  # 目标 concept_id -> 共现诗题列表
    if my_poetry_ids:
        others = (
            db.query(ConceptPoetryRel)
            .filter(ConceptPoetryRel.poetry_id.in_(my_poetry_ids), ConceptPoetryRel.concept_id != concept_id)
            .all()
        )
        for r in others:
            p = db.get(Poetry, r.poetry_id)
            if p:
                cooccur.setdefault(r.concept_id, [])
                if p.title not in cooccur[r.concept_id]:
                    cooccur[r.concept_id].append(p.title)
    node_ids.update(cooccur.keys())

    concepts = {x.id: x for x in db.query(Concept).filter(Concept.id.in_(node_ids)).all()}
    nodes = [{"id": x.id, "name": x.name, "theme_color": x.theme_color, "category": x.category} for x in concepts.values()]

    manual_pairs = {frozenset((e.from_concept_id, e.to_concept_id)) for e in edges}
    edge_items = [{
        "id": e.id,
        "from_id": e.from_concept_id, "to_id": e.to_concept_id,
        "from_name": concepts[e.from_concept_id].name, "to_name": concepts[e.to_concept_id].name,
        "relation_type": e.relation_type, "description": e.description, "auto": False,
    } for e in edges]
    # 共现边（若与人工边重复则合并进人工边的描述，不重复画线）
    for other_id, titles in cooccur.items():
        if other_id not in concepts:
            continue
        joined = "、".join(f"《{t}》" for t in titles[:4])
        desc = f"两意象共现于 {joined}{' 等' if len(titles) > 4 else ''}（由 {len(titles)} 篇共现作品自动推导）"
        if frozenset((concept_id, other_id)) in manual_pairs:
            for item in edge_items:
                if frozenset((item["from_id"], item["to_id"])) == frozenset((concept_id, other_id)):
                    item["description"] += " " + desc
        else:
            edge_items.append({
                "from_id": concept_id, "to_id": other_id,
                "from_name": concepts[concept_id].name, "to_name": concepts[other_id].name,
                "relation_type": "共现", "description": desc, "auto": True,
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
    svg = render_share_card(c, classic[0].clause if classic else "", classic[1] if classic else None)
    return Response(content=svg, media_type="image/svg+xml")
