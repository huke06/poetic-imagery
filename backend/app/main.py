"""FastAPI 应用入口"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import admin, agent, artwork, concept, poetry
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

app.include_router(concept.router)
app.include_router(poetry.router)
app.include_router(artwork.router)
app.include_router(agent.router)
app.include_router(admin.router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health():
    return {"code": 0, "msg": "ok", "data": {"status": "running", "service": "诗象志"}}
