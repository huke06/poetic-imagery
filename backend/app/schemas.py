"""Pydantic 请求/响应模型 v2"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


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
    category_main: str
    category_sub: str
    emotion_tags: list[str]
    theme_color: str
    is_featured: bool = False
    classic_clause: Optional[str] = None
    artwork_thumb: Optional[str] = None
    artwork_image: Optional[str] = None   # 标注精选艺术品高清图（无精选为 None）
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
    category_main: str
    category_sub: str
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
    category: str = ""
    category_main: str = ""
    category_sub: str = ""
    original_meaning: str = ""
    poetic_meaning: str = ""
    emotion_tags: str = ""
    origin_dynasty: str = ""
    peak_dynasty: str = ""
    description: str = ""
    aliases: str = ""
    theme_color: str = ""


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
    concepts: list[dict]
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
    dynasty_period: str = ""
    image_url: str
    thumb_url: str


class ArtworkDetail(BaseModel):
    id: int
    name: str
    artist: str
    dynasty_period: str = ""
    material: str
    size: str
    subject_names: list[str]
    image_url: str
    thumb_url: str
    description: str
    concepts: list[dict]


# ─────────── 意象关联 ───────────
class CooccurrenceStats(BaseModel):
    same_sentence: int = 0
    adjacent_sentence: int = 0
    same_poem: int = 0
    npmi: float = 0.0


class RelationEdge(BaseModel):
    id: int = 0
    from_id: int
    to_id: int
    from_name: str
    to_name: str
    relation_type: str
    description: str
    auto: bool = False
    cooccurrence: CooccurrenceStats | None = None       # 共现统计（NPMI 连线粗细）


class RelationGraph(BaseModel):
    nodes: list[dict]
    edges: list[RelationEdge]


# ─────────── 智能问答 ───────────
class AskReq(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    history: list[dict] = Field(default_factory=list)  # [{"role":"user"|"ai","content":"..."}] 多轮对话历史


class AskResp(BaseModel):
    answer: str
    source: str = "local"
    references: dict = Field(default_factory=dict)


class ComposeReq(BaseModel):
    concepts: list[str] = Field(..., min_length=1, max_length=5)
    style: str = "五言绝句"
    theme: str = ""


class ComposeResp(BaseModel):
    poem: str
    title: str
    style: str
    source: str = "local"
    tones: list[dict] = Field(default_factory=list)
    note: str = ""


# ─────────── 管理后台 ───────────
class RelationUpsert(BaseModel):
    from_concept_id: int
    to_concept_id: int
    relation_type: str = "共现"
    description: str = ""
    cooccurrence_type: str = ""      # 句内/跨句/全诗
    npmi: float = 0.0
    diaphaneity: float = 0.2
    verse: str = ""
