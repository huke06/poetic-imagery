# -*- coding: utf-8 -*-
"""数据库迁移（v2 → v3，幂等，启动时自动执行）

v3 变更：
- concept_poetry_rel 增加 emotion_main（一级情感标签）
- artwork 增加 dynasty_main（主朝代，用于检索统计）
- concept 增加 usage_summary（AI 用法谱系总结缓存）
- concept_relation 增加 cooccurrence_type / diaphaneity / verse（聚焦共现分析）
- 新增 cooccurrence_stat / emotion_stat / dynasty_occurrence_stat 三张统计表
- couplet.concept_id 允许为空（CSV 批量导入的对仗词可能暂无对应意象）
"""
from sqlalchemy import text
from sqlalchemy.engine import Engine

# (表, 列, DDL 片段)
ADD_COLUMNS = [
    ("concept_poetry_rel", "emotion_main", "VARCHAR(32) NOT NULL DEFAULT ''"),
    ("artwork", "dynasty_main", "VARCHAR(32) NOT NULL DEFAULT ''"),
    ("concept", "usage_summary", "TEXT NOT NULL DEFAULT ''"),
    ("concept_relation", "cooccurrence_type", "VARCHAR(16) NOT NULL DEFAULT ''"),
    ("concept_relation", "diaphaneity", "FLOAT NOT NULL DEFAULT 0.2"),
    ("concept_relation", "verse", "VARCHAR(255) NOT NULL DEFAULT ''"),
]


def _existing_cols(conn, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {r[1] for r in rows}


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"), {"n": table}
    ).fetchone()
    return row is not None


def _migrate_couplet_nullable(conn):
    """重建 couplet 表使 concept_id 可为空（SQLite 不支持直接 ALTER 约束）"""
    cols = conn.execute(text("PRAGMA table_info(couplet)")).fetchall()
    for cid, name, ctype, notnull, *_ in cols:
        if name == "concept_id" and notnull:
            break
    else:
        return
    conn.execute(text(
        "CREATE TABLE couplet_new ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " concept_id INTEGER REFERENCES concept(id) ON DELETE CASCADE,"
        " word_a VARCHAR(32) NOT NULL,"
        " word_b VARCHAR(32) NOT NULL,"
        " verse VARCHAR(255) NOT NULL,"
        " source VARCHAR(255) NOT NULL DEFAULT '')"))
    conn.execute(text(
        "INSERT INTO couplet_new(id, concept_id, word_a, word_b, verse, source)"
        " SELECT id, concept_id, word_a, word_b, verse, source FROM couplet"))
    conn.execute(text("DROP TABLE couplet"))
    conn.execute(text("ALTER TABLE couplet_new RENAME TO couplet"))
    conn.execute(text("CREATE INDEX ix_couplet_concept_id ON couplet(concept_id)"))


def run_migrations(engine: Engine):
    with engine.begin() as conn:
        # 仅 SQLite 需要迁移；其他数据库交给 create_all / DBA
        if engine.dialect.name != "sqlite":
            return
        for table, col, ddl in ADD_COLUMNS:
            if not _table_exists(conn, table):
                continue
            if col not in _existing_cols(conn, table):
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))
        if _table_exists(conn, "couplet"):
            _migrate_couplet_nullable(conn)
