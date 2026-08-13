# -*- coding: utf-8 -*-
"""向量索引构建 + 语义检索

- concepts 集合：意象本体（名称/别称/诗义/情感/分类）
- clauses  集合：名句（诗句/情感/作者/朝代/篇名/关联意象）

索引为空时惰性构建；数据变化后可调用 build_index(force=True) 重建。
"""
import hashlib
import threading
import time

from sqlalchemy.orm import Session

from ..models import Concept, ConceptPoetryRel, ConceptRelation, Couplet, Poetry
from ..utils import embedding
from . import vector_store

CONCEPTS_COLL = "concepts"
CLAUSES_COLL = "clauses"

# 语义相似度阈值（余弦距离，越小越相似；0~2）
CONCEPT_DIST_TH = 0.55
CLAUSE_DIST_TH = 0.65


def _hash_text(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _concept_text(c: Concept) -> str:
    """意象完整文本：名称/别称/分类/本义/诗义/情感/起源鼎盛/演变/用法谱系"""
    aliases = (c.aliases or "").replace(",", " ")
    tags = (c.emotion_tags or "").replace(",", " ")
    return " ".join(filter(None, [
        c.name, aliases, c.category_main or "", c.category_sub or "",
        "本义:" + (c.original_meaning or ""),
        "诗义:" + (c.poetic_meaning or ""),
        "情感:" + tags,
        "起源:" + (c.origin_dynasty or ""), "鼎盛:" + (c.peak_dynasty or ""),
        "演变:" + (c.description or ""),
        "用法谱系:" + (c.usage_summary or ""),
    ]))


def _collect_concepts(db: Session) -> list[tuple]:
    """返回 (id, text, metadata) 列表，text 额外附对仗/共现关键词"""
    concepts = db.query(Concept).all()
    id2name = {c.id: c.name for c in concepts}

    couplet_map: dict[int, list[str]] = {}
    for cp in db.query(Couplet).all():
        if cp.concept_id:
            couplet_map.setdefault(cp.concept_id, []).append(f"{cp.word_a}-{cp.word_b}")

    rel_map: dict[int, list[str]] = {}
    for r in db.query(ConceptRelation).all():
        if r.from_concept_id in id2name and r.to_concept_id in id2name:
            rel_map.setdefault(r.from_concept_id, []).append(id2name[r.to_concept_id])
            rel_map.setdefault(r.to_concept_id, []).append(id2name[r.from_concept_id])

    out = []
    for c in concepts:
        text = _concept_text(c)
        extras = []
        if c.id in couplet_map:
            extras.append("对仗:" + " ".join(couplet_map[c.id][:8]))
        if c.id in rel_map:
            extras.append("关联意象:" + " ".join(rel_map[c.id][:10]))
        if extras:
            text += " " + " ".join(extras)
        out.append((f"c{c.id}", text, {
            "concept_id": c.id, "name": c.name, "theme_color": c.theme_color or "",
            "category_main": c.category_main or "", "category_sub": c.category_sub or "",
        }))
    return out


def build_concepts(db: Session) -> int:
    items = _collect_concepts(db)
    if not items:
        return 0
    texts = [it[1] for it in items]
    embs = embedding.embed_texts(texts, batch_size=8)
    if embs is None:
        return 0
    vector_store.delete_collection(CONCEPTS_COLL)
    vector_store.upsert(
        CONCEPTS_COLL,
        ids=[it[0] for it in items],
        embeddings=embs,
        documents=texts,
        metadatas=[{**it[2], "text_hash": _hash_text(t)} for it, t in zip(items, texts)],
    )
    return len(items)


def build_clauses(db: Session) -> int:
    rows = (
        db.query(ConceptPoetryRel, Poetry, Concept)
        .join(Poetry, ConceptPoetryRel.poetry_id == Poetry.id)
        .join(Concept, ConceptPoetryRel.concept_id == Concept.id)
        .all()
    )
    if not rows:
        return 0
    items = []
    for rel, p, c in rows:
        items.append({
            "rid": rel.id,
            "concept_id": c.id, "concept_name": c.name,
            "poetry_id": p.id, "title": p.title, "author": p.author, "dynasty": p.dynasty,
            "clause": rel.clause, "emotion": rel.emotion or "", "is_classic": int(rel.is_classic or 0),
            "weight": rel.weight or 1,
        })
    texts = [f"{it['clause']} 情感:{it['emotion']} {it['dynasty']}{it['author']}《{it['title']}》" for it in items]
    embs = embedding.embed_texts(texts, batch_size=8)
    if embs is None:
        return 0
    vector_store.delete_collection(CLAUSES_COLL)
    vector_store.upsert(
        CLAUSES_COLL,
        ids=[f"r{it['rid']}" for it in items],
        embeddings=embs,
        documents=texts,
        metadatas=[{
            "rid": it["rid"], "concept_id": it["concept_id"], "concept_name": it["concept_name"],
            "poetry_id": it["poetry_id"], "title": it["title"], "author": it["author"],
            "dynasty": it["dynasty"], "clause": it["clause"], "emotion": it["emotion"],
            "is_classic": it["is_classic"], "weight": it["weight"],
            "text_hash": _hash_text(t),
        } for it, t in zip(items, texts)],
    )
    return len(items)


def build_index(db: Session, force: bool = False) -> dict:
    if not embedding.embedding_available():
        return {"available": False, "concepts": 0, "clauses": 0}
    if force or vector_store.collection_count(CONCEPTS_COLL) == 0:
        build_concepts(db)
    if force or vector_store.collection_count(CLAUSES_COLL) == 0:
        build_clauses(db)
    return {"available": True,
            "concepts": vector_store.collection_count(CONCEPTS_COLL),
            "clauses": vector_store.collection_count(CLAUSES_COLL)}


def semantic_search(db: Session, query: str, top_k: int = 6) -> dict:
    """语义检索：返回 {concepts:[...], clauses:[...]}"""
    if not embedding.embedding_available():
        return {"concepts": [], "clauses": []}
    qv = embedding.embed_text(query)
    if not qv:
        return {"concepts": [], "clauses": []}

    concepts = []
    if vector_store.collection_count(CONCEPTS_COLL) > 0:
        for hit in vector_store.query(CONCEPTS_COLL, qv, n_results=top_k):
            if hit["distance"] > CONCEPT_DIST_TH:
                continue
            m = hit["metadata"]
            cid = int(m.get("concept_id") or 0)
            if cid:
                concepts.append({"concept_id": cid, "name": m.get("name", ""),
                                 "distance": hit["distance"]})

    clauses = []
    if vector_store.collection_count(CLAUSES_COLL) > 0:
        for hit in vector_store.query(CLAUSES_COLL, qv, n_results=top_k * 2):
            if hit["distance"] > CLAUSE_DIST_TH:
                continue
            m = hit["metadata"]
            clauses.append({
                "poetry_id": int(m.get("poetry_id") or 0),
                "concept_id": int(m.get("concept_id") or 0),
                "concept_name": m.get("concept_name", ""),
                "title": m.get("title", ""), "author": m.get("author", ""),
                "dynasty": m.get("dynasty", ""), "clause": m.get("clause", ""),
                "emotion": m.get("emotion", ""), "is_classic": m.get("is_classic", 0),
                "distance": hit["distance"],
            })
    return {"concepts": concepts, "clauses": clauses}
def _collect_clauses(db: Session) -> list[tuple]:
    """返回 (rid, text, metadata) 三元组列表"""
    rows = (
        db.query(ConceptPoetryRel, Poetry, Concept)
        .join(Poetry, ConceptPoetryRel.poetry_id == Poetry.id)
        .join(Concept, ConceptPoetryRel.concept_id == Concept.id)
        .all()
    )
    out = []
    for rel, p, c in rows:
        text = f"{rel.clause} 情感:{rel.emotion or ''} {p.dynasty}{p.author}《{p.title}》"
        out.append((f"r{rel.id}", text, {
            "rid": rel.id, "concept_id": c.id, "concept_name": c.name,
            "poetry_id": p.id, "title": p.title, "author": p.author,
            "dynasty": p.dynasty, "clause": rel.clause, "emotion": rel.emotion or "",
            "is_classic": int(rel.is_classic or 0), "weight": rel.weight or 1,
        }))
    return out


def _upsert_batch(name: str, items: list[tuple]) -> int:
    """items: list of (id, text, metadata)；仅对这批做向量化并 upsert"""
    if not items:
        return 0
    embs = embedding.embed_texts([it[1] for it in items], batch_size=8)
    if embs is None:
        return 0
    vector_store.upsert(
        name,
        ids=[it[0] for it in items],
        embeddings=embs,
        documents=[it[1] for it in items],
        metadatas=[{**it[2], "text_hash": _hash_text(it[1])} for it in items],
    )
    return len(items)


def refresh_incremental(db: Session) -> dict:
    """增量刷新：仅对新增/变更条目重新向量化，删除已移除条目（不重算全量）"""
    stats = {"available": False, "concepts_added": 0, "concepts_deleted": 0,
             "clauses_added": 0, "clauses_deleted": 0}
    if not embedding.embedding_available():
        return stats
    stats["available"] = True

    # ── concepts ──
    col = vector_store.get_collection(CONCEPTS_COLL)
    existing = col.get(include=["metadatas"])
    ex_ids = existing.get("ids") or []
    ex_meta = existing.get("metadatas") or []
    ex_hash = {i: (m or {}).get("text_hash", "") for i, m in zip(ex_ids, ex_meta)}
    items = _collect_concepts(db)
    to_upsert = [it for it in items if it[0] not in ex_hash or ex_hash.get(it[0]) != _hash_text(it[1])]
    stats["concepts_added"] = _upsert_batch(CONCEPTS_COLL, to_upsert)
    db_ids = {it[0] for it in items}
    to_delete = [cid for cid in ex_ids if cid not in db_ids]
    if to_delete:
        col.delete(ids=to_delete)
        stats["concepts_deleted"] = len(to_delete)

    # ── clauses ──
    col2 = vector_store.get_collection(CLAUSES_COLL)
    existing2 = col2.get(include=["metadatas"])
    ex_ids2 = existing2.get("ids") or []
    ex_meta2 = existing2.get("metadatas") or []
    ex_hash2 = {i: (m or {}).get("text_hash", "") for i, m in zip(ex_ids2, ex_meta2)}
    items = _collect_clauses(db)
    to_upsert2 = [it for it in items if it[0] not in ex_hash2 or ex_hash2.get(it[0]) != _hash_text(it[1])]
    stats["clauses_added"] = _upsert_batch(CLAUSES_COLL, to_upsert2)
    db_ids2 = {it[0] for it in items}
    to_delete2 = [cid for cid in ex_ids2 if cid not in db_ids2]
    if to_delete2:
        col2.delete(ids=to_delete2)
        stats["clauses_deleted"] = len(to_delete2)

    return stats


_refresh_pending = threading.Event()
_refresh_lock = threading.Lock()


def schedule_incremental_refresh():
    """数据变更后调度一次后台增量刷新（1 秒去抖，避免频繁调用重复计算）"""
    if not embedding.embedding_available():
        return
    with _refresh_lock:
        if _refresh_pending.is_set():
            return
        _refresh_pending.set()

    def worker():
        try:
            time.sleep(1.0)
        finally:
            _refresh_pending.clear()
        from ..database import SessionLocal
        db = SessionLocal()
        try:
            refresh_incremental(db)
        except Exception:
            pass
        finally:
            db.close()

    threading.Thread(target=worker, daemon=True).start()

