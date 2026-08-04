"""数据库模型：v3（情感标签占比·朝代频次·共现统计）"""
from datetime import datetime
from typing import Optional

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
    usage_summary: Mapped[str] = mapped_column(Text, default="")  # 缓存的 AI 用法谱系总结
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
    translation: Mapped[str] = mapped_column(Text, default="")    # 缓存的现代汉语翻译
    appreciation: Mapped[str] = mapped_column(Text, default="")   # 缓存的文学赏析
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
    emotion_main: Mapped[str] = mapped_column(String(32), default="")  # 一级情感标签（七大类）
    weight: Mapped[int] = mapped_column(Integer, default=1)
    is_classic: Mapped[int] = mapped_column(Integer, default=0)
    annotation: Mapped[str] = mapped_column(Text, default="")  # 缓存的逐句笺注

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
    dynasty_main: Mapped[str] = mapped_column(String(32), default="", index=True)  # 主朝代（识别自朝代·时期）
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
    """意象关联表（知识网络）——v3 起聚焦共现分析"""
    __tablename__ = "concept_relation"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    from_concept_id: Mapped[int] = mapped_column(ForeignKey("concept.id", ondelete="CASCADE"), index=True)
    to_concept_id: Mapped[int] = mapped_column(ForeignKey("concept.id", ondelete="CASCADE"), index=True)
    relation_type: Mapped[str] = mapped_column(String(32), default="共现")  # v3：只保留共现
    description: Mapped[str] = mapped_column(String(255), default="")
    cooccurrence_type: Mapped[str] = mapped_column(String(16), default="")  # 句内/跨句/全诗
    same_sentence: Mapped[int] = mapped_column(Integer, default=0)   # 句内共现次数
    adjacent_sentence: Mapped[int] = mapped_column(Integer, default=0)  # 邻句共现次数
    same_poem: Mapped[int] = mapped_column(Integer, default=0)         # 全诗共现次数
    npmi: Mapped[float] = mapped_column(Float, default=0.0)            # 归一化点互信息 [-1, 1]
    diaphaneity: Mapped[float] = mapped_column(Float, default=0.2)     # 线条透明度（0.2 为最低值）
    verse: Mapped[str] = mapped_column(String(255), default="")        # 共现例句


class CooccurrenceStat(Base):
    """共现分析统计表（词对级，来自 cooccurrence_result.csv 等分析结果）"""
    __tablename__ = "cooccurrence_stat"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    word_a: Mapped[str] = mapped_column(String(32), index=True)
    word_b: Mapped[str] = mapped_column(String(32), index=True)
    cooccurrence_type: Mapped[str] = mapped_column(String(16), default="")  # 句内/跨句/全诗
    same_sentence: Mapped[int] = mapped_column(Integer, default=0)
    adjacent_sentence: Mapped[int] = mapped_column(Integer, default=0)
    same_poem: Mapped[int] = mapped_column(Integer, default=0)
    npmi: Mapped[float] = mapped_column(Float, default=0.0)
    diaphaneity: Mapped[float] = mapped_column(Float, default=0.2)
    verse: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")


class EmotionStat(Base):
    """意象情感标签占比统计（来自 imagery_emotion_statistics_aggregated.csv）"""
    __tablename__ = "emotion_stat"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(32), index=True)
    emotion: Mapped[str] = mapped_column(String(32))        # 二级情感标签
    category: Mapped[str] = mapped_column(String(32))       # 一级情感标签
    count: Mapped[int] = mapped_column(Integer, default=0)
    ratio: Mapped[float] = mapped_column(Float, default=0.0)


class DynastyOccurrenceStat(Base):
    """意象朝代出现频次统计（来自 dynasty_occurrence.csv，归并为九大朝代段）"""
    __tablename__ = "dynasty_occurrence_stat"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(String(32), index=True)
    dynasty: Mapped[str] = mapped_column(String(16))   # 先秦/秦汉/魏晋南北朝/隋唐/五代十国/宋/元/明/清
    count: Mapped[int] = mapped_column(Integer, default=0)


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
    concept_id: Mapped[Optional[int]] = mapped_column(ForeignKey("concept.id", ondelete="CASCADE"), index=True, nullable=True)
    word_a: Mapped[str] = mapped_column(String(32))
    word_b: Mapped[str] = mapped_column(String(32))
    verse: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(255), default="")

    concept: Mapped[Concept] = relationship(back_populates="couplets")


class AtlasPainting(Base):
    """诗意图鉴画卷（后台可编辑管理）"""
    __tablename__ = "atlas_painting"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(128))
    en: Mapped[str] = mapped_column(String(255), default="")
    image_url: Mapped[str] = mapped_column(String(512), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    dots: Mapped[list["AtlasDot"]] = relationship(back_populates="painting", cascade="all, delete-orphan")


class AtlasDot(Base):
    """诗意图鉴画卷上的意象标注圆点"""
    __tablename__ = "atlas_dot"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    painting_id: Mapped[int] = mapped_column(ForeignKey("atlas_painting.id", ondelete="CASCADE"), index=True)
    left_pct: Mapped[float] = mapped_column(Float, default=50.0)   # 横向位置百分比 0-100
    top_pct: Mapped[float] = mapped_column(Float, default=50.0)    # 纵向位置百分比 0-100
    label: Mapped[str] = mapped_column(String(32))                 # 意象名（圆点标签）
    poem: Mapped[str] = mapped_column(String(255), default="")     # 意象基本内容（诗句）
    desc: Mapped[str] = mapped_column(Text, default="")            # 意象阐释说明
    concept_id: Mapped[Optional[int]] = mapped_column(ForeignKey("concept.id", ondelete="SET NULL"), nullable=True)

    painting: Mapped[AtlasPainting] = relationship(back_populates="dots")


class User(Base):
    """用户表"""
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(128), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user")  # user / admin
    avatar: Mapped[str] = mapped_column(String(512), default="")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    is_active: Mapped[int] = mapped_column(Integer, default=1)

    conversations: Mapped[list["ChatConversation"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class ChatConversation(Base):
    """聊天会话"""
    __tablename__ = "chat_conversation"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(128), default="新对话")
    source: Mapped[str] = mapped_column(String(16), default="ask")  # ask / compose
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    update_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    user: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class ChatMessage(Base):
    """聊天消息"""
    __tablename__ = "chat_message"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("chat_conversation.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))           # user / ai
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(16), default="")  # llm / llm_free / local
    references_json: Mapped[str] = mapped_column(Text, default="{}")  # 引用的 JSON
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    conversation: Mapped[ChatConversation] = relationship(back_populates="messages")
