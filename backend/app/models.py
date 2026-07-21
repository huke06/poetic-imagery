"""数据库模型：方案中的 7 张核心表 + 扩展 couplet 表

扩展说明（对方案的优化）：
1. concept_poetry_rel 增加 emotion 字段 —— 情感分布图直接由真实关联数据计算，无需硬编码
2. 新增 couplet 表 —— 「对仗与意象关联区」所需的对仗词组数据本地化
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Concept(Base):
    """意象主表"""
    __tablename__ = "concept"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(32), default="天象")
    original_meaning: Mapped[str] = mapped_column(Text, default="")
    poetic_meaning: Mapped[str] = mapped_column(Text, default="")
    emotion_tags: Mapped[str] = mapped_column(String(255), default="")  # 逗号分隔
    origin_dynasty: Mapped[str] = mapped_column(String(32), default="")
    peak_dynasty: Mapped[str] = mapped_column(String(32), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    aliases: Mapped[str] = mapped_column(String(255), default="")  # 别称，逗号分隔
    theme_color: Mapped[str] = mapped_column(String(16), default="#2B4C7E")  # 卡片主题色
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
    source_writing_id: Mapped[str] = mapped_column(String(64), default="")  # 上游 writingId（如有）
    title: Mapped[str] = mapped_column(String(255), index=True)
    author: Mapped[str] = mapped_column(String(64), index=True)
    dynasty: Mapped[str] = mapped_column(String(32), index=True)
    writing_type: Mapped[str] = mapped_column(String(32), default="诗")  # 诗/词/曲/文
    content: Mapped[str] = mapped_column(Text)
    clauses: Mapped[str] = mapped_column(Text, default="[]")  # JSON 数组字符串
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    concept_rels: Mapped[list["ConceptPoetryRel"]] = relationship(back_populates="poetry", cascade="all, delete-orphan")


class ConceptPoetryRel(Base):
    """意象-诗文关联表（含具体诗句、情感归属、名句权重）"""
    __tablename__ = "concept_poetry_rel"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concept.id", ondelete="CASCADE"), index=True)
    poetry_id: Mapped[int] = mapped_column(ForeignKey("poetry.id", ondelete="CASCADE"), index=True)
    clause: Mapped[str] = mapped_column(String(255))       # 含该意象的诗句
    emotion: Mapped[str] = mapped_column(String(32), default="")  # 该句在此意象下的情感归属
    weight: Mapped[int] = mapped_column(Integer, default=1)  # 关联权重（名句优先级）
    is_classic: Mapped[int] = mapped_column(Integer, default=0)  # 是否经典名句

    concept: Mapped[Concept] = relationship(back_populates="poetry_rels")
    poetry: Mapped[Poetry] = relationship(back_populates="concept_rels")


class Artwork(Base):
    """艺术品表"""
    __tablename__ = "artwork"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_work_id: Mapped[str] = mapped_column(String(64), default="")
    name: Mapped[str] = mapped_column(String(255), index=True)
    artist: Mapped[str] = mapped_column(String(64), default="佚名")
    dynasty: Mapped[str] = mapped_column(String(32), index=True)
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
    relation_desc: Mapped[str] = mapped_column(String(255), default="")  # 关联阐释
    weight: Mapped[int] = mapped_column(Integer, default=1)

    concept: Mapped[Concept] = relationship(back_populates="artwork_rels")
    artwork: Mapped[Artwork] = relationship(back_populates="concept_rels")


class ConceptRelation(Base):
    """意象关联表（知识网络）"""
    __tablename__ = "concept_relation"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    from_concept_id: Mapped[int] = mapped_column(ForeignKey("concept.id", ondelete="CASCADE"), index=True)
    to_concept_id: Mapped[int] = mapped_column(ForeignKey("concept.id", ondelete="CASCADE"), index=True)
    relation_type: Mapped[str] = mapped_column(String(32))  # 对仗/共现/情感同源/演变衍生
    description: Mapped[str] = mapped_column(String(255), default="")


class DynastyStats(Base):
    """朝代统计表（预计算，供可视化直接调用）"""
    __tablename__ = "dynasty_stats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concept.id", ondelete="CASCADE"), index=True)
    dynasty: Mapped[str] = mapped_column(String(32))
    count: Mapped[int] = mapped_column(Integer, default=0)

    concept: Mapped[Concept] = relationship(back_populates="dynasty_stats")


class Couplet(Base):
    """对仗词组表（扩展）：意象高频对仗词与对应律句"""
    __tablename__ = "couplet"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concept.id", ondelete="CASCADE"), index=True)
    word_a: Mapped[str] = mapped_column(String(32))   # 对仗词甲
    word_b: Mapped[str] = mapped_column(String(32))   # 对仗词乙
    verse: Mapped[str] = mapped_column(String(255))   # 例句
    source: Mapped[str] = mapped_column(String(255), default="")  # 出处（作者《篇目》）

    concept: Mapped[Concept] = relationship(back_populates="couplets")
