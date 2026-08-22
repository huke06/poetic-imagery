"""艺术品模块接口"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Artwork, Concept, ConceptArtworkRel
from ..schemas import ApiResp
from ..utils.taxonomy import ARTWORK_DYNASTY_GROUPS, split_subjects

router = APIRouter(prefix="/api/artwork", tags=["艺术品"])


@router.get("/list")
def artwork_list(
    dynasty: str = Query("", description="主朝代筛选"),
    subject: str = Query("", description="主题筛选"),
    keyword: str = Query("", description="名称/作者关键词"),
    featured: str = Query("", description="传任意非空值即仅返回首页精选艺术品"),
    page: int = Query(1, ge=1), page_size: int = Query(12, ge=1, le=300),
    db: Session = Depends(get_db),
):
    q = db.query(Artwork)
    if featured and featured.lower() in ("1", "true", "yes"):
        q = q.filter(Artwork.is_featured == 1)
    if dynasty:
        q = q.filter(Artwork.dynasty_main == dynasty)
    if subject:
        q = q.filter(Artwork.subject_names.like(f"%{subject}%"))
    if keyword:
        like = f"%{keyword}%"
        q = q.filter((Artwork.name.like(like)) | (Artwork.artist.like(like)))
    total = q.count()
    if featured and featured.lower() in ("1", "true", "yes"):
        rows = q.order_by(func.random()).limit(page_size).all()
    else:
        rows = q.order_by(Artwork.id).offset((page - 1) * page_size).limit(page_size).all()

    # 主朝代统计（可识别、可检索）：九大段 + 近现代/当代（艺术品不限古诗朝代），附每段数量
    counts = dict(db.query(Artwork.dynasty_main, func.count(Artwork.id))
                  .group_by(Artwork.dynasty_main).all())
    dynasties = [{"name": g, "count": counts.get(g, 0)} for g in ARTWORK_DYNASTY_GROUPS if counts.get(g)]

    subjects = sorted({s for a in db.query(Artwork.subject_names).all() for s in split_subjects(a[0])})
    return ApiResp(data={
        "total": total, "page": page, "page_size": page_size,
        "filters": {"dynasties": dynasties, "subjects": subjects},
        "items": [{"id": a.id, "name": a.name, "artist": a.artist,
                   "dynasty_period": a.dynasty_period or a.dynasty,
                   "dynasty_main": a.dynasty_main,
                   "image_url": a.image_url, "thumb_url": a.thumb_url or a.image_url} for a in rows],
    })


@router.get("/{artwork_id}")
def artwork_detail(artwork_id: int, db: Session = Depends(get_db)):
    a = db.get(Artwork, artwork_id)
    if not a:
        raise HTTPException(404, "艺术品不存在")
    rels = db.query(ConceptArtworkRel).filter_by(artwork_id=a.id).all()
    concepts = []
    for r in rels:
        c = db.get(Concept, r.concept_id)
        if c:
            concepts.append({"id": c.id, "name": c.name, "theme_color": c.theme_color, "relation_desc": r.relation_desc})
    return ApiResp(data={
        "id": a.id, "name": a.name, "artist": a.artist, "dynasty_period": a.dynasty_period or a.dynasty,
        "dynasty_main": a.dynasty_main,
        "material": a.material, "size": a.size,
        "subject_names": split_subjects(a.subject_names),
        "image_url": a.image_url, "thumb_url": a.thumb_url or a.image_url,
        "description": a.description, "concepts": concepts,
    })
