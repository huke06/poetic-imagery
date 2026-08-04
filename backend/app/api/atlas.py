"""诗意图鉴模块接口：公开翻页浏览 + 后台管理（图片上传、圆点标注工作台）"""
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AtlasDot, AtlasPainting
from ..schemas import ApiResp
from .admin import check_token

router = APIRouter(prefix="/api/atlas", tags=["诗意图鉴"])

STATIC_ATLAS_DIR = Path(__file__).resolve().parent.parent / "static" / "atlas"


def _painting_public(p: AtlasPainting) -> dict:
    """转为前台 PoeticAtlasView 使用的数据结构"""
    dots = []
    imageries = {}
    for d in sorted(p.dots, key=lambda x: x.id):
        dots.append({"left": f"{d.left_pct:.2f}%", "top": f"{d.top_pct:.2f}%", "label": d.label})
        imageries[d.label] = {"poem": d.poem, "desc": d.desc, "conceptId": d.concept_id}
    return {"id": p.id, "title": p.title, "en": p.en, "src": p.image_url,
            "dots": dots, "imageries": imageries}


# ═══════════ 公开接口 ═══════════
@router.get("/paintings")
def atlas_paintings(db: Session = Depends(get_db)):
    """诗意图鉴画卷列表（含圆点标注），按 sort_order 排序"""
    paintings = db.query(AtlasPainting).order_by(AtlasPainting.sort_order, AtlasPainting.id).all()
    return ApiResp(data={"paintings": [_painting_public(p) for p in paintings]})


# ═══════════ 管理接口 ═══════════
class PaintingUpsert(BaseModel):
    title: str
    en: str = ""
    image_url: str = ""
    sort_order: int = 0


class DotIn(BaseModel):
    left_pct: float = 50.0
    top_pct: float = 50.0
    label: str
    poem: str = ""
    desc: str = ""
    concept_id: Optional[int] = None


class DotsSave(BaseModel):
    dots: list[DotIn]


@router.get("/admin/list", dependencies=[Depends(check_token)])
def admin_atlas_list(db: Session = Depends(get_db)):
    paintings = db.query(AtlasPainting).order_by(AtlasPainting.sort_order, AtlasPainting.id).all()
    items = []
    for p in paintings:
        dots = [{"id": d.id, "left_pct": d.left_pct, "top_pct": d.top_pct, "label": d.label,
                 "poem": d.poem, "desc": d.desc, "concept_id": d.concept_id}
                for d in sorted(p.dots, key=lambda x: x.id)]
        items.append({"id": p.id, "title": p.title, "en": p.en, "image_url": p.image_url,
                      "sort_order": p.sort_order, "dots": dots})
    return ApiResp(data=items)


@router.post("/admin", dependencies=[Depends(check_token)])
def admin_create_painting(req: PaintingUpsert, db: Session = Depends(get_db)):
    p = AtlasPainting(title=req.title, en=req.en, image_url=req.image_url, sort_order=req.sort_order)
    db.add(p)
    db.commit()
    return ApiResp(data={"id": p.id})


@router.put("/admin/{pid}", dependencies=[Depends(check_token)])
def admin_update_painting(pid: int, req: PaintingUpsert, db: Session = Depends(get_db)):
    p = db.get(AtlasPainting, pid)
    if not p:
        raise HTTPException(404, "画卷不存在")
    p.title, p.en, p.sort_order = req.title, req.en, req.sort_order
    if req.image_url:
        p.image_url = req.image_url
    db.commit()
    return ApiResp(data={"id": p.id})


@router.delete("/admin/{pid}", dependencies=[Depends(check_token)])
def admin_delete_painting(pid: int, db: Session = Depends(get_db)):
    p = db.get(AtlasPainting, pid)
    if not p:
        raise HTTPException(404, "画卷不存在")
    db.delete(p)
    db.commit()
    return ApiResp()


@router.post("/admin/{pid}/image", dependencies=[Depends(check_token)])
async def admin_upload_atlas_image(pid: int, file: UploadFile, db: Session = Depends(get_db)):
    """上传画卷图片到 /static/atlas/"""
    p = db.get(AtlasPainting, pid)
    if not p:
        raise HTTPException(404, "画卷不存在")
    suffix = Path(file.filename or "img.jpg").suffix.lower()
    if suffix not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        raise HTTPException(400, "仅支持 jpg/png/webp/gif")
    STATIC_ATLAS_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"atlas_{pid}{suffix}"
    with open(STATIC_ATLAS_DIR / fname, "wb") as f:
        shutil.copyfileobj(file.file, f)
    url = f"/static/atlas/{fname}"
    p.image_url = url
    db.commit()
    return ApiResp(data={"image_url": url})


@router.put("/admin/{pid}/dots", dependencies=[Depends(check_token)])
def admin_save_dots(pid: int, req: DotsSave, db: Session = Depends(get_db)):
    """整批保存圆点标注（以提交列表为准，先删后增）"""
    p = db.get(AtlasPainting, pid)
    if not p:
        raise HTTPException(404, "画卷不存在")
    db.query(AtlasDot).filter_by(painting_id=pid).delete()
    for d in req.dots:
        db.add(AtlasDot(painting_id=pid, left_pct=d.left_pct, top_pct=d.top_pct,
                        label=d.label, poem=d.poem, desc=d.desc, concept_id=d.concept_id))
    db.commit()
    return ApiResp(data={"count": len(req.dots)})
