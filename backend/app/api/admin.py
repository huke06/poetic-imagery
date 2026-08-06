"""管理后台模块：数据总览 / 系统配置 / 意象·诗文·古画·对仗·关联 CRUD

鉴权：所有接口需请求头 X-Admin-Token（与生效配置中的 ADMIN_TOKEN 一致）
"""
import json
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import config_store
from ..config import settings
from ..database import get_db
from ..models import (
    Artwork, Concept, ConceptArtworkRel, ConceptPoetryRel, ConceptRelation, Couplet, DynastyStats, Poetry, User,
)
from .. import auth as auth_utils
from ..schemas import ApiResp, ConceptUpsert, RelationUpsert
from ..utils.palette import assign_color, palette_for_category

router = APIRouter(prefix="/api/admin", tags=["管理后台"])

STATIC_ART_DIR = Path(__file__).resolve().parent.parent / "static" / "artworks"

# ── 导入模板（兜底内容；优先读取项目根目录 templates/ 下的文件） ──
JSON_TEMPLATE_FALLBACK = json.dumps({
    "concept": {"name": "意象名（必填）", "category": "天象/植物/动物/器物/地理/人事", "theme_color": "",
                "aliases": "别称1,别称2", "original_meaning": "本义", "poetic_meaning": "引申义",
                "emotion_tags": "情感1,情感2,情感3,情感4", "origin_dynasty": "先秦", "peak_dynasty": "唐",
                "description": "演变史"},
    "poetries": [{"title": "篇目名", "author": "作者", "dynasty": "唐", "writing_type": "诗",
                  "content": "全文，换行用 \n",
                  "translation": "（选填）现代汉语翻译，留空由 AI 自动补全",
                  "appreciation": "（选填）文学赏析，留空由 AI 自动补全",
                  "rels": [{"clause": "含意象的诗句", "emotion": "情感标签之一", "is_classic": 1, "weight": 3}]}],
    "couplets": [{"word_a": "对仗词甲", "word_b": "对仗词乙", "verse": "例句", "source": "作者《篇目》"}],
    "artworks": [{"name": "画名", "artist": "作者", "dynasty": "宋", "material": "绢本设色", "size": "",
                  "subject_names": "中国绘画;山水", "description": "简介", "relation_desc": "诗画关联阐释", "weight": 2}],
    "relations": [{"to": "月", "relation_type": "共现", "description": "关系说明"}],
}, ensure_ascii=False, indent=2)

CSV_POETRIES_FALLBACK = """concept_name,concept_category,concept_tags,title,author,dynasty,writing_type,content,clause,emotion,is_classic,weight,translation,appreciation
雁,动物,思乡 离别 孤寂 时光流逝,次北固山下,王湾,唐,诗,"客路青山外，行舟绿水前。\n潮平两岸阔，风正一帆悬。\n海日生残夜，江春入旧年。\n乡书何处达？归雁洛阳边。",乡书何处达？归雁洛阳边,思乡,1,3,"旅客路过青山之外，行舟在绿水之前……","首联点题，写羁旅之行……（可留空，留空时由 AI 自动生成）"
"""

CSV_CONCEPTS_FALLBACK = """name,category,aliases,emotion_tags,origin_dynasty,peak_dynasty,theme_color,original_meaning,poetic_meaning,description
雁,动物,"大雁,鸿雁,归雁,孤雁",思乡 离别 孤寂 时光流逝,先秦,唐宋,,"候鸟，秋来南去，春来北归。","雁的迁徙与书信传说使其成为思乡与离别的经典意象。","雁意象起于《诗经》……"
"""

CSV_COUPLETS_FALLBACK = """word_a,word_b,verse,source
月,霜,床前明月光，疑是地上霜,李白《静夜思》
"""

CSV_COOCCURRENCE_FALLBACK = """name,to,cooccurrence_type,NPMI,diaphaneity,verse,description
月,霜,句内,0.65,0.8,床前明月光，疑是地上霜,月色如霜，清冷之景常相映衬
"""

CSV_ARTWORKS_FALLBACK = """name,artist,dynasty_period,material,size,subject_names,image_url,description,concepts,relation_desc
对月图,马远,宋代·南宋,绢本设色,23.5x24.6cm,中国绘画;山水,,月下独酌，水天一色，意境空灵,月,画中孤月高悬，与诗词「明月出天山」之境相通
"""

CSV_DYNASTY_FALLBACK = """word,dynasty,count
天,先秦,139
天,秦汉,334
天,魏晋南北朝,1620
天,隋唐,11679
天,五代十国,716
天,宋,61978
天,元,25605
天,明,122097
天,清,120374
"""

CSV_EMOTION_STATS_FALLBACK = """word,different_emotion_count,total_emotion_occurrences,emotion_names,emotion_categories,emotion_counts,emotion_ratios,emotion_details
天,8,20,季节感怀;时光流逝;自然赞美,自然山水类;人生感悟类;自然山水类,10;5;5,50.0%;25.0%;25.0%,"季节感怀[自然山水类](10/50.0%);时光流逝[人生感悟类](5/25.0%);自然赞美[自然山水类](5/25.0%)"
"""


def check_token(x_admin_token: str = Header(default="")):
    token = config_store.get_effective("ADMIN_TOKEN", settings.ADMIN_TOKEN)
    if x_admin_token != token:
        raise HTTPException(401, "管理令牌无效")


def _split_clauses(content: str) -> list[str]:
    from scripts.seed import split_clauses
    return split_clauses(content)


# ═══════════ 数据总览 ═══════════
@router.get("/overview", dependencies=[Depends(check_token)])
def overview(db: Session = Depends(get_db)):
    from ..utils import llm
    return ApiResp(data={
        "concepts": db.query(Concept).count(),
        "poetries": db.query(Poetry).count(),
        "artworks": db.query(Artwork).count(),
        "concept_poetry_rels": db.query(ConceptPoetryRel).count(),
        "concept_relations": db.query(ConceptRelation).count(),
        "couplets": db.query(Couplet).count(),
        "llm_configured": llm.llm_available(),
        "concept_list": [
            {"id": c.id, "name": c.name, "category_main": c.category_main, "category_sub": c.category_sub,
             "theme_color": c.theme_color}
            for c in db.query(Concept).order_by(Concept.id).all()
        ],
    })


# ═══════════ 系统配置（热生效） ═══════════
@router.get("/config", dependencies=[Depends(check_token)])
def get_config():
    env_fallback = {
        "LLM_API_KEY": settings.LLM_API_KEY, "LLM_BASE_URL": settings.LLM_BASE_URL,
        "LLM_MODEL": settings.LLM_MODEL,
        "UPSTREAM_WRITING_BASE": settings.UPSTREAM_WRITING_BASE,
        "UPSTREAM_BOOK_BASE": settings.UPSTREAM_BOOK_BASE,
        "ADMIN_TOKEN": "（已设置）" if settings.ADMIN_TOKEN else "",
    }
    return ApiResp(data=config_store.all_effective(env_fallback))


class ConfigUpdate(BaseModel):
    changes: dict


@router.put("/config", dependencies=[Depends(check_token)])
def put_config(req: ConfigUpdate):
    config_store.update(req.changes)
    return ApiResp(msg="配置已保存并即时生效（密钥类字段留空表示回落环境变量）")


# ═══════════ 配色体系 ═══════════
@router.get("/palette", dependencies=[Depends(check_token)])
def palette(name: str = "", category: str = ""):
    """按分类返回传统色卡；传 name 时给出该意象的推荐色"""
    data = {"family_colors": palette_for_category(category)}
    if name:
        data["suggested"] = assign_color(name, category)
    return ApiResp(data=data)


# ═══════════ 意象 CRUD ═══════════
@router.post("/concept", dependencies=[Depends(check_token)])
def create_concept(req: ConceptUpsert, db: Session = Depends(get_db)):
    if db.query(Concept).filter_by(name=req.name).first():
        raise HTTPException(400, "同名意象已存在")
    payload = req.model_dump()
    from ..utils.palette import LEGACY_CATEGORY_MAP
    if not payload.get("category_main") and payload.get("category"):
        main, sub = LEGACY_CATEGORY_MAP.get(payload["category"], ("自然类", ""))
        payload["category_main"] = main
        payload["category_sub"] = sub
    if not payload.get("theme_color"):
        payload["theme_color"] = assign_color(req.name, payload.get("category_main", ""))["color"]
    obj = Concept(**payload)
    db.add(obj)
    db.commit()
    return ApiResp(data={"id": obj.id, "theme_color": obj.theme_color})


@router.put("/concept/{concept_id}", dependencies=[Depends(check_token)])
def update_concept(concept_id: int, req: ConceptUpsert, db: Session = Depends(get_db)):
    obj = db.get(Concept, concept_id)
    if not obj:
        raise HTTPException(404, "意象不存在")
    for k, v in req.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    return ApiResp(data={"id": obj.id})


@router.post("/concept/{concept_id}/feature", dependencies=[Depends(check_token)])
def toggle_featured(concept_id: int, featured: bool = Query(...), db: Session = Depends(get_db)):
    """切换首页精选推荐状态"""
    obj = db.get(Concept, concept_id)
    if not obj:
        raise HTTPException(404, "意象不存在")
    obj.is_featured = featured
    db.commit()
    return ApiResp(data={"id": obj.id, "is_featured": obj.is_featured})


@router.delete("/concept/{concept_id}", dependencies=[Depends(check_token)])
def delete_concept(concept_id: int, db: Session = Depends(get_db)):
    obj = db.get(Concept, concept_id)
    if not obj:
        raise HTTPException(404, "意象不存在")
    db.delete(obj)
    db.commit()
    return ApiResp()


# ═══════════ 诗文 CRUD（含意象关联） ═══════════
class PoetryRelIn(BaseModel):
    concept_id: int
    clause: str
    emotion: str = ""
    is_classic: int = 0
    weight: int = 1


class PoetryUpsert(BaseModel):
    title: str
    author: str = "佚名"
    dynasty: str = ""
    writing_type: str = "诗"
    content: str
    source_writing_id: str = ""
    rels: list[PoetryRelIn] = Field(default_factory=list)


def _poetry_full(p: Poetry, db: Session) -> dict:
    rels = []
    for r in db.query(ConceptPoetryRel).filter_by(poetry_id=p.id).all():
        c = db.get(Concept, r.concept_id)
        rels.append({"rel_id": r.id, "concept_id": r.concept_id, "concept_name": c.name if c else "?",
                     "clause": r.clause, "emotion": r.emotion, "is_classic": r.is_classic, "weight": r.weight})
    return {"id": p.id, "title": p.title, "author": p.author, "dynasty": p.dynasty,
            "writing_type": p.writing_type, "content": p.content,
            "source_writing_id": p.source_writing_id, "rels": rels}


@router.get("/poetry/list", dependencies=[Depends(check_token)])
def admin_poetry_list(keyword: str = "", page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50),
                      db: Session = Depends(get_db)):
    q = db.query(Poetry)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter((Poetry.title.like(like)) | (Poetry.author.like(like)) | (Poetry.content.like(like)))
    total = q.count()
    rows = q.order_by(Poetry.id).offset((page - 1) * page_size).limit(page_size).all()
    return ApiResp(data={"total": total, "page": page,
                         "items": [_poetry_full(p, db) for p in rows]})


@router.post("/poetry", dependencies=[Depends(check_token)])
def create_poetry(req: PoetryUpsert, db: Session = Depends(get_db)):
    obj = Poetry(title=req.title, author=req.author, dynasty=req.dynasty,
                 writing_type=req.writing_type, content=req.content,
                 source_writing_id=req.source_writing_id,
                 clauses=json.dumps(_split_clauses(req.content), ensure_ascii=False))
    db.add(obj)
    db.flush()
    for r in req.rels:
        db.add(ConceptPoetryRel(poetry_id=obj.id, **r.model_dump()))
    db.commit()
    return ApiResp(data={"id": obj.id})


@router.put("/poetry/{poetry_id}", dependencies=[Depends(check_token)])
def update_poetry(poetry_id: int, req: PoetryUpsert, db: Session = Depends(get_db)):
    obj = db.get(Poetry, poetry_id)
    if not obj:
        raise HTTPException(404, "诗文不存在")
    obj.title, obj.author, obj.dynasty = req.title, req.author, req.dynasty
    obj.writing_type, obj.content = req.writing_type, req.content
    obj.source_writing_id = req.source_writing_id
    obj.clauses = json.dumps(_split_clauses(req.content), ensure_ascii=False)
    # 关联：以提交列表为准做差量更新（先删后增，保持简单可靠）
    db.query(ConceptPoetryRel).filter_by(poetry_id=obj.id).delete()
    for r in req.rels:
        db.add(ConceptPoetryRel(poetry_id=obj.id, **r.model_dump()))
    db.commit()
    return ApiResp(data={"id": obj.id})


@router.delete("/poetry/{poetry_id}", dependencies=[Depends(check_token)])
def delete_poetry(poetry_id: int, db: Session = Depends(get_db)):
    obj = db.get(Poetry, poetry_id)
    if not obj:
        raise HTTPException(404, "诗文不存在")
    db.delete(obj)
    db.commit()
    return ApiResp()


# ═══════════ 古画 CRUD 与图片接入 ═══════════
class ArtworkUpsert(BaseModel):
    name: str
    artist: str = "佚名"
    dynasty: str = ""
    material: str = ""
    size: str = ""
    subject_names: str = ""
    description: str = ""
    image_url: str = ""          # 方式一：外链图片 URL
    source_work_id: str = ""
    concept_ids: list[int] = Field(default_factory=list)  # 关联意象
    relation_desc: str = ""


def _artwork_full(a: Artwork, db: Session) -> dict:
    rels = [{"concept_id": r.concept_id, "relation_desc": r.relation_desc,
             "concept_name": (db.get(Concept, r.concept_id) or Concept(name="?")).name}
            for r in db.query(ConceptArtworkRel).filter_by(artwork_id=a.id).all()]
    return {"id": a.id, "name": a.name, "artist": a.artist, "dynasty": a.dynasty,
            "dynasty_main": a.dynasty_main,
            "material": a.material, "size": a.size, "subject_names": a.subject_names,
            "description": a.description, "image_url": a.image_url, "thumb_url": a.thumb_url,
            "source_work_id": a.source_work_id, "rels": rels}


@router.get("/artwork/list", dependencies=[Depends(check_token)])
def admin_artwork_list(keyword: str = "", page: int = Query(1, ge=1), page_size: int = Query(12, ge=1, le=60),
                       db: Session = Depends(get_db)):
    q = db.query(Artwork)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter((Artwork.name.like(like)) | (Artwork.artist.like(like)))
    total = q.count()
    rows = q.order_by(Artwork.id).offset((page - 1) * page_size).limit(page_size).all()
    return ApiResp(data={"total": total, "page": page, "items": [_artwork_full(a, db) for a in rows]})


@router.post("/artwork", dependencies=[Depends(check_token)])
def create_artwork(req: ArtworkUpsert, db: Session = Depends(get_db)):
    from ..utils.taxonomy import normalize_artwork_dynasty
    obj = Artwork(name=req.name, artist=req.artist, dynasty=req.dynasty, material=req.material,
                  size=req.size, subject_names=req.subject_names, description=req.description,
                  image_url=req.image_url, thumb_url=req.image_url, source_work_id=req.source_work_id,
                  dynasty_main=normalize_artwork_dynasty("", req.dynasty))
    db.add(obj)
    db.flush()
    for cid in req.concept_ids:
        db.add(ConceptArtworkRel(concept_id=cid, artwork_id=obj.id, relation_desc=req.relation_desc, weight=2))
    db.commit()
    return ApiResp(data={"id": obj.id})


@router.put("/artwork/{artwork_id}", dependencies=[Depends(check_token)])
def update_artwork(artwork_id: int, req: ArtworkUpsert, db: Session = Depends(get_db)):
    from ..utils.taxonomy import normalize_artwork_dynasty
    obj = db.get(Artwork, artwork_id)
    if not obj:
        raise HTTPException(404, "艺术品不存在")
    obj.name, obj.artist, obj.dynasty = req.name, req.artist, req.dynasty
    obj.material, obj.size, obj.subject_names = req.material, req.size, req.subject_names
    obj.description, obj.source_work_id = req.description, req.source_work_id
    obj.dynasty_main = normalize_artwork_dynasty(getattr(obj, "dynasty_period", ""), req.dynasty)
    if req.image_url:
        obj.image_url = req.image_url
        obj.thumb_url = req.image_url
    db.query(ConceptArtworkRel).filter_by(artwork_id=obj.id).delete()
    for cid in req.concept_ids:
        db.add(ConceptArtworkRel(concept_id=cid, artwork_id=obj.id, relation_desc=req.relation_desc, weight=2))
    db.commit()
    return ApiResp(data={"id": obj.id})


@router.post("/artwork/{artwork_id}/feature", dependencies=[Depends(check_token)])
def toggle_artwork_featured(artwork_id: int, concept_id: int = Query(...), featured: bool = Query(...), db: Session = Depends(get_db)):
    """切换艺术品精选状态（同一意象仅一幅精选，切换时自动取消旧的）"""
    rel = db.query(ConceptArtworkRel).filter_by(artwork_id=artwork_id, concept_id=concept_id).first()
    if not rel:
        raise HTTPException(404, "该意象-艺术品关联不存在")
    if featured:
        # 取消该意象其他艺术品的精选
        db.query(ConceptArtworkRel).filter(
            ConceptArtworkRel.concept_id == concept_id,
            ConceptArtworkRel.id != rel.id,
            ConceptArtworkRel.is_featured == True,
        ).update({ConceptArtworkRel.is_featured: False})
    rel.is_featured = featured
    db.commit()
    return ApiResp(data={"rel_id": rel.id, "is_featured": rel.is_featured})


@router.delete("/artwork/{artwork_id}", dependencies=[Depends(check_token)])
def delete_artwork(artwork_id: int, db: Session = Depends(get_db)):
    obj = db.get(Artwork, artwork_id)
    if not obj:
        raise HTTPException(404, "古画不存在")
    db.delete(obj)
    db.commit()
    return ApiResp()


@router.post("/artwork/{artwork_id}/image", dependencies=[Depends(check_token)])
async def upload_artwork_image(artwork_id: int, file: UploadFile, db: Session = Depends(get_db)):
    """方式二：本地上传图片文件，保存到 /static/artworks/ 并更新记录"""
    obj = db.get(Artwork, artwork_id)
    if not obj:
        raise HTTPException(404, "古画不存在")
    suffix = Path(file.filename or "img.jpg").suffix.lower()
    if suffix not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        raise HTTPException(400, "仅支持 jpg/png/webp/gif")
    STATIC_ART_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"artwork_upload_{artwork_id}{suffix}"
    with open(STATIC_ART_DIR / fname, "wb") as f:
        shutil.copyfileobj(file.file, f)
    url = f"/static/artworks/{fname}"
    obj.image_url, obj.thumb_url = url, url
    db.commit()
    return ApiResp(data={"image_url": url})


@router.post("/artwork/{artwork_id}/svg", dependencies=[Depends(check_token)])
def regenerate_artwork_svg(artwork_id: int, theme: str = "", db: Session = Depends(get_db)):
    """方式三：重新生成国风水墨占位图（月/夕阳/青绿 三种主题）"""
    obj = db.get(Artwork, artwork_id)
    if not obj:
        raise HTTPException(404, "古画不存在")
    from scripts.svg_art import make_svg
    from scripts.svg_art import _detect_theme
    theme_name = _detect_theme(obj.name, obj.description, theme)
    STATIC_ART_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"artwork_{artwork_id:02d}.svg"
    (STATIC_ART_DIR / fname).write_text(make_svg(theme_name, obj.name, obj.artist, obj.dynasty), encoding="utf-8")
    url = f"/static/artworks/{fname}"
    obj.image_url, obj.thumb_url = url, url
    db.commit()
    return ApiResp(data={"image_url": url, "theme": theme_name})


# ═══════════ 对仗 CRUD ═══════════
class CoupletUpsert(BaseModel):
    concept_id: int
    word_a: str
    word_b: str
    verse: str
    source: str = ""


@router.get("/couplet/list", dependencies=[Depends(check_token)])
def couplet_list(concept_id: int = 0, db: Session = Depends(get_db)):
    q = db.query(Couplet)
    if concept_id:
        q = q.filter_by(concept_id=concept_id)
    rows = q.order_by(Couplet.concept_id, Couplet.id).all()
    items = []
    for cp in rows:
        c = db.get(Concept, cp.concept_id)
        items.append({"id": cp.id, "concept_id": cp.concept_id, "concept_name": c.name if c else "?",
                      "word_a": cp.word_a, "word_b": cp.word_b, "verse": cp.verse, "source": cp.source})
    return ApiResp(data=items)


@router.post("/couplet", dependencies=[Depends(check_token)])
def create_couplet(req: CoupletUpsert, db: Session = Depends(get_db)):
    obj = Couplet(**req.model_dump())
    db.add(obj)
    db.commit()
    return ApiResp(data={"id": obj.id})


@router.put("/couplet/{couplet_id}", dependencies=[Depends(check_token)])
def update_couplet(couplet_id: int, req: CoupletUpsert, db: Session = Depends(get_db)):
    obj = db.get(Couplet, couplet_id)
    if not obj:
        raise HTTPException(404, "对仗不存在")
    for k, v in req.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    return ApiResp(data={"id": obj.id})


@router.delete("/couplet/{couplet_id}", dependencies=[Depends(check_token)])
def delete_couplet(couplet_id: int, db: Session = Depends(get_db)):
    obj = db.get(Couplet, couplet_id)
    if not obj:
        raise HTTPException(404, "对仗不存在")
    db.delete(obj)
    db.commit()
    return ApiResp()


# ═══════════ 意象关联 CRUD 与自动推导 ═══════════
@router.post("/relation", dependencies=[Depends(check_token)])
def create_relation(req: RelationUpsert, db: Session = Depends(get_db)):
    payload = req.model_dump()
    payload["relation_type"] = "共现"  # v3：关联类型聚焦共现分析
    obj = ConceptRelation(**payload)
    db.add(obj)
    db.commit()
    return ApiResp(data={"id": obj.id})


@router.delete("/relation/{relation_id}", dependencies=[Depends(check_token)])
def delete_relation(relation_id: int, db: Session = Depends(get_db)):
    obj = db.get(ConceptRelation, relation_id)
    if not obj:
        raise HTTPException(404, "关联不存在")
    db.delete(obj)
    db.commit()
    return ApiResp()


@router.get("/relation-suggestions", dependencies=[Depends(check_token)])
def relation_suggestions(db: Session = Depends(get_db)):
    """基于真实数据自动推导意象关联建议：
    1. 共现：两意象关联到同一首诗（附共现作品清单）
    2. 情感同源：两意象的情感标签存在交集
    已人工建立的关联会标注 exists=true
    """
    concepts = {c.id: c for c in db.query(Concept).all()}
    rels = db.query(ConceptPoetryRel).all()
    # concept_id -> {poetry_id: [clauses]}
    by_concept: dict[int, dict[int, list[str]]] = {}
    for r in rels:
        by_concept.setdefault(r.concept_id, {}).setdefault(r.poetry_id, []).append(r.clause)

    existing = {(e.from_concept_id, e.to_concept_id) for e in db.query(ConceptRelation).all()}
    suggestions = []
    ids = sorted(by_concept.keys())
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            shared = set(by_concept[a]) & set(by_concept[b])
            ca, cb = concepts.get(a), concepts.get(b)
            if not ca or not cb:
                continue
            emo_a = set(ca.emotion_tags.split(",")) - {""}
            emo_b = set(cb.emotion_tags.split(",")) - {""}
            shared_emo = sorted(emo_a & emo_b)
            if not shared and not shared_emo:
                continue
            shared_titles = [db.get(Poetry, pid).title for pid in sorted(shared) if db.get(Poetry, pid)]
            suggestions.append({
                "from_id": a, "from_name": ca.name, "to_id": b, "to_name": cb.name,
                "shared_poetries": shared_titles, "shared_emotions": shared_emo,
                "score": len(shared) * 2 + len(shared_emo),
                "exists": (a, b) in existing or (b, a) in existing,
            })
    suggestions.sort(key=lambda x: x["score"], reverse=True)
    return ApiResp(data=suggestions)


# ═══════════ 批量导入（JSON/CSV 文件上传） ═══════════
PACK_FREE_FORMATS = {"csv-couplets", "csv-cooccurrence", "csv-emotion_stats", "csv-dynasty_stats", "csv-artworks"}


def _parse_one(filename: str, text: str):
    """解析单个文件 → (fmt, packs, errors, warns)"""
    from ..service import importer
    errors: list[str] = []
    warns: list[str] = []
    if filename.endswith(".json"):
        try:
            packs = importer.parse_json(text)
        except json.JSONDecodeError as e:
            raise HTTPException(400, f"{filename}：JSON 解析失败：{e}")
        fmt = "json"
    elif filename.endswith(".csv"):
        fmt0, packs, errors = importer.parse_csv(text)
        if packs is None:
            raise HTTPException(400, f"{filename}：" + (errors[0] if errors else "CSV 解析失败"))
        fmt = f"csv-{fmt0}"
    else:
        raise HTTPException(400, f"{filename}：仅支持 .json 或 .csv 文件")
    if fmt not in PACK_FREE_FORMATS:
        for pack in packs:
            e, w = importer.validate(pack)
            errors += [f"[{filename}] {x}" for x in e]
            warns += [f"[{filename}] {x}" for x in w]
    return fmt, packs, errors, warns


@router.post("/import", dependencies=[Depends(check_token)])
async def import_file(files: list[UploadFile], dry_run: bool = Query(False), db: Session = Depends(get_db)):
    """批量导入：上传一个或多个 .json / .csv 文件（可本体表+诗文表+JSON 混合同传）

    - dry_run=true 时只校验与预览，不落库
    - JSON：单意象对象 / {"concepts": [...]} / 顶层数组（结构同 concept_template.json）
    - CSV：按表头自动识别「诗文关联表 / 意象本体表 / 对仗表 / 共现分析表 / 情感统计表 / 朝代频次表」
    """
    from ..service import importer

    all_packs: list[tuple[str, list[dict]]] = []
    errors: list[str] = []
    warns: list[str] = []
    previews = []

    for f in files:
        raw = await f.read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(400, f"{f.filename}：文件编码需为 UTF-8（Excel 导出 CSV 时请选择「CSV UTF-8」）")
        fmt, packs, e, w = _parse_one((f.filename or "").lower(), text)
        errors += e
        warns += w
        all_packs.append((fmt, packs))
        previews.append(importer.build_import_preview(packs, fmt))

    # 结合库状态的校验（新意象必须有情感标签；补充包可省略；专项 CSV 不参与意象校验）
    for fmt, packs in all_packs:
        if fmt in PACK_FREE_FORMATS:
            continue
        for pack in packs:
            errors += importer.validate_against_db(db, pack)

    preview = {
        "files": len(files),
        "concept_count": sum(p["concept_count"] for p in previews),
        "concepts": [n for p in previews for n in p["concepts"]],
        "poetry_rows": sum(p["poetry_rows"] for p in previews),
        "rel_rows": sum(p["rel_rows"] for p in previews),
        "couplet_rows": sum(p["couplet_rows"] for p in previews),
        "artwork_rows": sum(p["artwork_rows"] for p in previews),
        "special_rows": {p["format"]: p.get("row_count", 0) for p in previews
                         if p["format"] in PACK_FREE_FORMATS},
        "formats": [p["format"] for p in previews],
    }
    if errors:
        return ApiResp(code=1, msg=f"校验未通过：{len(errors)} 处错误",
                       data={"preview": preview, "errors": errors, "warnings": warns})
    if dry_run:
        return ApiResp(msg="校验通过（预览模式，未落库）",
                       data={"preview": preview, "errors": [], "warnings": warns, "reports": []})

    reports = []
    try:
        for fmt, packs in all_packs:
            if fmt == "csv-couplets":
                reports.append({"type": "couplets", **importer.import_couplets_csv(db, packs)})
            elif fmt == "csv-cooccurrence":
                reports.append({"type": "cooccurrence", **importer.import_cooccurrence_csv(db, packs)})
            elif fmt == "csv-emotion_stats":
                reports.append({"type": "emotion_stats", **importer.import_emotion_stats_csv(db, packs)})
            elif fmt == "csv-dynasty_stats":
                reports.append({"type": "dynasty_stats", **importer.import_dynasty_stats_csv(db, packs)})
            elif fmt == "csv-artworks":
                reports.append({"type": "artworks", **importer.import_artworks_csv(db, packs)})
            else:
                for pack in packs:
                    reports.append(importer.import_concept_data(db, pack))
        db.commit()

        # 自动触发诗文角色分析（后台异步，不阻塞导入响应）
        import threading
        def _auto_analyze():
            from ..api.concept import analyze_roles_for_concept
            from ..database import SessionLocal as AutoDB
            auto_db = AutoDB()
            try:
                ids = [cid for (cid,) in auto_db.query(Concept.id).join(
                    ConceptPoetryRel, ConceptPoetryRel.concept_id == Concept.id
                ).filter(ConceptPoetryRel.role_in_poem == "").distinct().all()]
                for cid in ids:
                    analyze_roles_for_concept(auto_db, cid)
                auto_db.commit()
            finally:
                auto_db.close()
        threading.Thread(target=_auto_analyze, daemon=True).start()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"导入失败，已回滚：{e}")
    return ApiResp(msg=f"导入完成：{len(reports)} 批数据",
                   data={"preview": preview, "errors": [], "warnings": warns, "reports": reports})


@router.get("/import/template")
def import_template(format: str = Query(
        "json", pattern="^(json|csv_poetries|csv_concepts|csv_couplets|csv_cooccurrence|csv_artworks|csv_dynasty_stats|csv_emotion_stats)$")):
    """下载统一导入模板（文件存放于项目根目录 templates/，可直接编辑后上传）"""
    from fastapi.responses import PlainTextResponse

    files = {
        "json": ("concept_template.json", JSON_TEMPLATE_FALLBACK),
        "csv_poetries": ("poetries_template.csv", CSV_POETRIES_FALLBACK),
        "csv_concepts": ("concepts_template.csv", CSV_CONCEPTS_FALLBACK),
        "csv_couplets": ("couplets_template.csv", CSV_COUPLETS_FALLBACK),
        "csv_cooccurrence": ("cooccurrence_template.csv", CSV_COOCCURRENCE_FALLBACK),
        "csv_artworks": ("artworks_template.csv", CSV_ARTWORKS_FALLBACK),
        "csv_dynasty_stats": ("dynasty_stats_template.csv", CSV_DYNASTY_FALLBACK),
        "csv_emotion_stats": ("emotion_stats_template.csv", CSV_EMOTION_STATS_FALLBACK),
    }
    fname, fallback = files[format]
    tpl_path = Path(__file__).resolve().parent.parent.parent.parent / "templates" / fname
    content = tpl_path.read_text(encoding="utf-8") if tpl_path.exists() else fallback
    return PlainTextResponse(
        content, media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


# ═══════════ 用户管理 ═══════════
@router.get("/users", dependencies=[Depends(check_token)])
def admin_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id).all()
    return ApiResp(data=[{"id": u.id, "username": u.username, "email": u.email, "role": u.role,
                          "is_active": u.is_active, "create_time": str(u.create_time)} for u in users])


class UserUpsert(BaseModel):
    username: str = ""
    email: str = ""
    password: str = ""
    role: str = "user"
    is_active: bool = True


@router.post("/users", dependencies=[Depends(check_token)])
def admin_create_user(req: UserUpsert, db: Session = Depends(get_db)):
    if not req.username or not req.password:
        raise HTTPException(400, "用户名和密码必填")
    if db.query(User).filter_by(username=req.username).first():
        raise HTTPException(400, "用户名已存在")
    u = User(username=req.username, email=req.email, role=req.role or "user",
             password_hash=auth_utils.hash_pw(req.password), is_active=int(req.is_active))
    db.add(u)
    db.commit()
    return ApiResp(data={"id": u.id})


@router.put("/users/{user_id}", dependencies=[Depends(check_token)])
def admin_update_user(user_id: int, req: UserUpsert, db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "用户不存在")
    if req.username:
        u.username = req.username
    if req.email:
        u.email = req.email
    if req.password:
        u.password_hash = auth_utils.hash_pw(req.password)
    u.role = req.role or u.role
    u.is_active = int(req.is_active)
    db.commit()
    return ApiResp(data={"id": u.id})


@router.delete("/users/{user_id}", dependencies=[Depends(check_token)])
def admin_delete_user(user_id: int, db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "用户不存在")
    db.delete(u)
    db.commit()
    return ApiResp()


# ═══════════ 批量预生成 ═══════════
@router.post("/pregenerate", dependencies=[Depends(check_token)])
def pregenerate_all(db: Session = Depends(get_db)):
    """批量预生成所有未翻译/未赏析的诗文（Token 消耗大，建议非高峰期用）"""
    from ..api.poetry import pregenerate_for_poem
    poems = db.query(Poetry).all()
    total = len(poems)
    new_tr = new_ap = 0
    for i, p in enumerate(poems):
        had_tr, had_ap = bool(p.translation), bool(p.appreciation)
        pregenerate_for_poem(db, p)
        if not had_tr and p.translation:
            new_tr += 1
        if not had_ap and p.appreciation:
            new_ap += 1
        if (i + 1) % 20 == 0:
            db.commit()
    db.commit()
    return ApiResp(msg=f"处理 {total} 首，新增翻译 {new_tr} 条、赏析 {new_ap} 条")


@router.post("/stats/recompute", dependencies=[Depends(check_token)])
def recompute_stats(db: Session = Depends(get_db)):
    from scripts.seed_data import DYNASTY_ORDER
    db.query(DynastyStats).delete()
    n = 0
    for c in db.query(Concept).all():
        counts, seen = {}, set()
        for r in db.query(ConceptPoetryRel).filter_by(concept_id=c.id).all():
            dyn = r.poetry.dynasty
            if (dyn, r.poetry_id) not in seen:
                seen.add((dyn, r.poetry_id))
                counts[dyn] = counts.get(dyn, 0) + 1
        for dyn in DYNASTY_ORDER:
            if counts.get(dyn):
                db.add(DynastyStats(concept_id=c.id, dynasty=dyn, count=counts[dyn]))
                n += 1
    db.commit()
    return ApiResp(msg=f"朝代统计已重算（{n} 条）")


@router.post("/stats/analyze-roles", dependencies=[Depends(check_token)])
def analyze_roles(concept_id: int = Query(0, description="指定意象ID，0=全库"), db: Session = Depends(get_db)):
    """调用 LLM 批量分析意象在诗中的角色（用法谱系数据源）"""
    from ..api.concept import analyze_roles_for_concept
    from ..utils.llm import llm_available
    if not llm_available():
        return ApiResp(code=1, msg="LLM 未配置，无法分析")
    ids = [c.id for c in db.query(Concept).all()] if not concept_id else [concept_id]
    total = 0
    for cid in ids:
        n = analyze_roles_for_concept(db, cid)
        total += n
    db.commit()
    return ApiResp(data={"updated": total, "concepts": len(ids)})
