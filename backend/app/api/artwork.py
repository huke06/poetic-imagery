"""艺术品模块接口"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Artwork, Concept, ConceptArtworkRel
from ..schemas import ApiResp

router = APIRouter(prefix="/api/artwork", tags=["艺术品"])


@router.get("/list")
def artwork_list(
    dynasty: str = Query("", description="朝代筛选"),
    subject: str = Query("", description="主题筛选"),
    keyword: str = Query("", description="名称/作者关键词"),
    page: int = Query(1, ge=1), page_size: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    q = db.query(Artwork)
    if dynasty:
        q = q.filter(Artwork.dynasty == dynasty)
    if subject:
        q = q.filter(Artwork.subject_names.like(f"%{subject}%"))
    if keyword:
        like = f"%{keyword}%"
        q = q.filter((Artwork.name.like(like)) | (Artwork.artist.like(like)))
    total = q.count()
    rows = q.order_by(Artwork.id).offset((page - 1) * page_size).limit(page_size).all()
    dynasties = [r[0] for r in db.query(Artwork.dynasty).distinct().all()]
    subjects = sorted({s for a in db.query(Artwork.subject_names).all() for s in a[0].split(";") if s})
    return ApiResp(data={
        "total": total, "page": page, "page_size": page_size,
        "filters": {"dynasties": dynasties, "subjects": subjects},
        "items": [{"id": a.id, "name": a.name, "artist": a.artist, "dynasty": a.dynasty,
                   "image_url": a.image_url, "thumb_url": a.thumb_url} for a in rows],
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
        "id": a.id, "name": a.name, "artist": a.artist, "dynasty": a.dynasty,
        "material": a.material, "size": a.size,
        "subject_names": [s for s in a.subject_names.split(";") if s],
        "image_url": a.image_url, "thumb_url": a.thumb_url,
        "description": a.description, "concepts": concepts,
    })
