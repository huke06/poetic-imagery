"""Pydantic 请求/响应模型"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─────────── 通用 ───────────
class ApiResp(BaseModel):
    code: int = 0
    msg: str = "ok"
    data: Any = None


class PageReq(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=50)


# ─────────── 意象 ───────────
class ConceptBrief(BaseModel):
    id: int
    name: str
    category: str
    emotion_tags: list[str]
    theme_color: str
    classic_clause: Optional[str] = None   # 代表名句
    artwork_thumb: Optional[str] = None    # 关联古画缩略图
    poetry_count: int = 0

    class Config:
        from_attributes = True


class DynastyStatItem(BaseModel):
    dynasty: str
    count: int


class EmotionStatItem(BaseModel):
    emotion: str
    count: int


class CoupletItem(BaseModel):
    word_a: str
    word_b: str
    verse: str
    source: str


class ConceptDetail(BaseModel):
    id: int
    name: str
    category: str
    aliases: list[str]
    original_meaning: str
    poetic_meaning: str
    emotion_tags: list[str]
    origin_dynasty: str
    peak_dynasty: str
    description: str
    theme_color: str
    dynasty_stats: list[DynastyStatItem]
    emotion_stats: list[EmotionStatItem]
    couplets: list[CoupletItem]
    poetry_count: int
    artwork_count: int


class ConceptUpsert(BaseModel):
    name: str
    category: str = "天象"
    original_meaning: str = ""
    poetic_meaning: str = ""
    emotion_tags: str = ""
    origin_dynasty: str = ""
    peak_dynasty: str = ""
    description: str = ""
    aliases: str = ""
    theme_color: str = "#2B4C7E"


# ─────────── 诗文 ───────────
class PoetryBrief(BaseModel):
    id: int
    title: str
    author: str
    dynasty: str
    writing_type: str


class ClauseRelItem(BaseModel):
    rel_id: int
    clause: str
    emotion: str
    is_classic: int
    weight: int
    poetry: PoetryBrief


class PoetryDetail(BaseModel):
    id: int
    title: str
    author: str
    dynasty: str
    writing_type: str
    content: str
    clauses: list[str]
    concepts: list[dict]      # 诗中涉及的意象 [{id, name, clauses:[...]}]
    create_time: datetime


class PoetrySearchReq(BaseModel):
    key: str = ""
    dynasty: str = ""
    author: str = ""
    writing_type: str = ""
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=50)


# ─────────── 艺术品 ───────────
class ArtworkBrief(BaseModel):
    id: int
    name: str
    artist: str
    dynasty: str
    image_url: str
    thumb_url: str


class ArtworkDetail(BaseModel):
    id: int
    name: str
    artist: str
    dynasty: str
    material: str
    size: str
    subject_names: list[str]
    image_url: str
    thumb_url: str
    description: str
    concepts: list[dict]      # 相关意象 [{id, name, relation_desc}]


# ─────────── 意象关联 ───────────
class RelationEdge(BaseModel):
    from_id: int
    to_id: int
    from_name: str
    to_name: str
    relation_type: str
    description: str


class RelationGraph(BaseModel):
    nodes: list[dict]
    edges: list[RelationEdge]


# ─────────── 智能问答 ───────────
class AskReq(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)


class AskResp(BaseModel):
    answer: str
    source: str = "local"                 # local / llm
    references: dict = Field(default_factory=dict)  # {concepts, poetries, artworks}


class ComposeReq(BaseModel):
    concepts: list[str] = Field(..., min_length=1, max_length=5)
    style: str = "五言绝句"               # 五言绝句/七言绝句/五言律诗/七言律诗
    theme: str = ""                       # 可选情感基调


class ComposeResp(BaseModel):
    poem: str
    title: str
    style: str
    source: str = "local"
    tones: list[str] = Field(default_factory=list)  # 逐句平仄
    note: str = ""


# ─────────── 管理后台 ───────────
class RelationUpsert(BaseModel):
    from_concept_id: int
    to_concept_id: int
    relation_type: str
    description: str = ""
