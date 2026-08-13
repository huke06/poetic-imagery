# -*- coding: utf-8 -*-
"""ChromaDB 向量库封装（本地持久化，无服务）"""
from pathlib import Path

import chromadb

from ..config import settings

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
PERSIST_DIR = BASE_DIR / "chroma_data"

_client = None
_collections: dict[str, object] = {}


def _get_client():
    global _client
    if _client is None:
        PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(PERSIST_DIR))
    return _client


def _sanitize(meta: dict) -> dict:
    """ChromaDB 元数据只接受扁平 str/int/float/bool，None 转空串"""
    out = {}
    for k, v in (meta or {}).items():
        if v is None:
            v = ""
        if isinstance(v, (str, int, float, bool)):
            out[k] = v
        else:
            out[k] = str(v)
    return out


def get_collection(name: str):
    if name not in _collections:
        _collections[name] = _get_client().get_or_create_collection(
            name=name, metadata={"hnsw:space": "cosine"}
        )
    return _collections[name]


def collection_count(name: str) -> int:
    return get_collection(name).count()


def upsert(name: str, ids: list[str], embeddings: list[list[float]],
           documents: list[str], metadatas: list[dict] | None = None):
    if not ids:
        return
    col = get_collection(name)
    metas = [_sanitize(m) for m in (metadatas or [{} for _ in ids])]
    col.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metas)


def delete_collection(name: str):
    client = _get_client()
    try:
        client.delete_collection(name)
    except Exception:
        pass
    _collections.pop(name, None)


def query(name: str, query_embedding: list[float], n_results: int = 8,
          where: dict | None = None) -> list[dict]:
    col = get_collection(name)
    if col.count() == 0:
        return []
    n = min(n_results, col.count())
    res = col.query(
        query_embeddings=[query_embedding],
        n_results=n,
        where=where,
        include=["metadatas", "documents", "distances"],
    )
    ids = (res.get("ids") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    return [{"id": ids[i], "metadata": metas[i], "document": docs[i], "distance": dists[i]}
            for i in range(len(ids))]
