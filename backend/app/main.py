"""FastAPI 应用入口"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import admin, agent, artwork, atlas, auth, chat, concept, poetry
from .database import init_db

app = FastAPI(
    title="诗象志 · 古诗词意象智能体",
    description="基于意象知识图谱的古诗词文化智能体后端服务",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境放开；生产应限定前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态资源（本地生成的古画 SVG 等）
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(concept.router)
app.include_router(poetry.router)
app.include_router(artwork.router)
app.include_router(atlas.router)
app.include_router(agent.router)
app.include_router(admin.router)


@app.on_event("startup")
def startup():
    from .database import engine
    from .migrate import run_migrations
    run_migrations(engine)
    init_db()
    _run_backfill()


def _run_backfill():
    """启动回补：情感标签学习映射 + 一级情感标注 + 艺术品主朝代/封面图/主题格式兜底（幂等）"""
    from .database import SessionLocal
    from .models import Artwork
    from .service.importer import annotate_emotion_main
    from .utils.taxonomy import normalize_artwork_dynasty, normalize_subjects, rebuild_learned_map_from_db

    db = SessionLocal()
    try:
        rebuild_learned_map_from_db(db)
        annotate_emotion_main(db)
        changed = 0
        for a in db.query(Artwork).all():
            main = normalize_artwork_dynasty(a.dynasty_period, a.dynasty)
            if a.dynasty_main != main:
                a.dynasty_main = main
                changed += 1
            # 封面图兜底：真实作品图优先于水墨占位 SVG
            real_img = bool(a.image_url and not a.image_url.endswith(".svg"))
            if real_img and (not a.thumb_url or a.thumb_url.endswith(".svg")):
                a.thumb_url = a.image_url
                changed += 1
            # 主题归一化：中文分号/顿号/逗号 → 英文分号
            norm = normalize_subjects(a.subject_names)
            if norm != (a.subject_names or ""):
                a.subject_names = norm
                changed += 1
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"code": 0, "msg": "ok", "data": {"status": "running", "service": "诗象志"}}
