"""数据库模型：8 张表（v2：二级分类·共现统计·古画期代）"""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Concept(Base):
    """意象主表"""
    __tablename__ = "concept"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(32), default="")              # 保留兼容，不再使用
    category_main: Mapped[str] = mapped_column(String(32), default="自然类")   # 五大一级类目
    category_sub: Mapped[str] = mapped_column(String(64), default="")          # 二级类目
    original_meaning: Mapped[str] = mapped_column(Text, default="")
    poetic_meaning: Mapped[str] = mapped_column(Text, default="")
    emotion_tags: Mapped[str] = mapped_column(String(255), default="")  # 逗号分隔
    origin_dynasty: Mapped[str] = mapped_column(String(32), default="")
    peak_dynasty: Mapped[str] = mapped_column(String(32), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    aliases: Mapped[str] = mapped_column(String(255), default="")
    theme_color: Mapped[str] = mapped_column(String(16), default="#2B4C7E")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    update_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    poetry_rels: Mapped[list["ConceptPoetryRel"]] = relationship(back_populates="concept", cascade="all, delete-orphan")
    artwork_rels: Mapped[list["ConceptArtworkRel"]] = relationship(back_populates="concept", cascade="all, delete-orphan")
    dynasty_stats: Mapped[list["DynastyStats"]] = relationship(back_populates="concept", cascade="all, delete-orphan")
    couplets: Mapped[list["Couplet"]] = relationship(back_populates="concept", cascade="all, delete-orphan")


class Poetry(Base):
    """诗文表"""
    __tablename__ = "poetry"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_writing_id: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(255), index=True)
    author: Mapped[str] = mapped_column(String(64), index=True)
    dynasty: Mapped[str] = mapped_column(String(32), index=True)
    writing_type: Mapped[str] = mapped_column(String(32), default="诗")  # 诗/词/曲/文 及细类
    content: Mapped[str] = mapped_column(Text)
    clauses: Mapped[str] = mapped_column(Text, default="[]")  # JSON 数组字符串
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    concept_rels: Mapped[list["ConceptPoetryRel"]] = relationship(back_populates="poetry", cascade="all, delete-orphan")


class ConceptPoetryRel(Base):
    """意象-诗文关联表"""
    __tablename__ = "concept_poetry_rel"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concept.id", ondelete="CASCADE"), index=True)
    poetry_id: Mapped[int] = mapped_column(ForeignKey("poetry.id", ondelete="CASCADE"), index=True)
    clause: Mapped[str] = mapped_column(String(255))
    emotion: Mapped[str] = mapped_column(String(32), default="")
    weight: Mapped[int] = mapped_column(Integer, default=1)
    is_classic: Mapped[int] = mapped_column(Integer, default=0)

    concept: Mapped[Concept] = relationship(back_populates="poetry_rels")
    poetry: Mapped[Poetry] = relationship(back_populates="concept_rels")


class Artwork(Base):
    """艺术品表"""
    __tablename__ = "artwork"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_work_id: Mapped[str] = mapped_column(String(64), default="")
    name: Mapped[str] = mapped_column(String(255), index=True)
    artist: Mapped[str] = mapped_column(String(64), default="佚名")
    dynasty: Mapped[str] = mapped_column(String(32), default="")           # 保留兼容
    dynasty_period: Mapped[str] = mapped_column(String(64), default="")   # 朝代·时期（如 "清代·清雍正"）
    material: Mapped[str] = mapped_column(String(128), default="")
    size: Mapped[str] = mapped_column(String(64), default="")
    subject_names: Mapped[str] = mapped_column(String(255), default="")
    image_url: Mapped[str] = mapped_column(String(512), default="")
    thumb_url: Mapped[str] = mapped_column(String(512), default="")
    description: Mapped[str] = mapped_column(Text, default="")

    concept_rels: Mapped[list["ConceptArtworkRel"]] = relationship(back_populates="artwork", cascade="all, delete-orphan")


class ConceptArtworkRel(Base):
    """意象-艺术品关联表"""
    __tablename__ = "concept_artwork_rel"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concept.id", ondelete="CASCADE"), index=True)
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artwork.id", ondelete="CASCADE"), index=True)
    relation_desc: Mapped[str] = mapped_column(String(255), default="")
    weight: Mapped[int] = mapped_column(Integer, default=1)

    concept: Mapped[Concept] = relationship(back_populates="artwork_rels")
    artwork: Mapped[Artwork] = relationship(back_populates="concept_rels")


class ConceptRelation(Base):
    """意象关联表（知识网络）"""
    __tablename__ = "concept_relation"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    from_concept_id: Mapped[int] = mapped_column(ForeignKey("concept.id", ondelete="CASCADE"), index=True)
    to_concept_id: Mapped[int] = mapped_column(ForeignKey("concept.id", ondelete="CASCADE"), index=True)
    relation_type: Mapped[str] = mapped_column(String(32))  # 共现/对仗/情感同源/演变衍生
    description: Mapped[str] = mapped_column(String(255), default="")
    same_sentence: Mapped[int] = mapped_column(Integer, default=0)   # 句内共现次数
    adjacent_sentence: Mapped[int] = mapped_column(Integer, default=0)  # 邻句共现次数
    same_poem: Mapped[int] = mapped_column(Integer, default=0)         # 全诗共现次数
    npmi: Mapped[float] = mapped_column(Float, default=0.0)            # 归一化点互信息 [-1, 1]


class DynastyStats(Base):
    """朝代统计表"""
    __tablename__ = "dynasty_stats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concept.id", ondelete="CASCADE"), index=True)
    dynasty: Mapped[str] = mapped_column(String(32))
    count: Mapped[int] = mapped_column(Integer, default=0)

    concept: Mapped[Concept] = relationship(back_populates="dynasty_stats")


class Couplet(Base):
    """对仗词组表"""
    __tablename__ = "couplet"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concept.id", ondelete="CASCADE"), index=True)
    word_a: Mapped[str] = mapped_column(String(32))
    word_b: Mapped[str] = mapped_column(String(32))
    verse: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(255), default="")

    concept: Mapped[Concept] = relationship(back_populates="couplets")
