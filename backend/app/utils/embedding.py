# -*- coding: utf-8 -*-
"""Qwen 多模态向量化客户端（阿里云百炼 DashScope · qwen3-vl-embedding）

未配置 EMBEDDING_API_KEY 时 embedding_available() 返回 False，RAG 自动回退关键词检索。
"""
import httpx

from ..config import settings


def embedding_available() -> bool:
    return bool(settings.EMBEDDING_API_KEY)


def _call(payload: dict) -> list[list[float]] | None:
    """调用原生多模态 embedding 端点；失败返回 None"""
    try:
        resp = httpx.post(
            settings.EMBEDDING_BASE_URL,
            headers={"Authorization": f"Bearer {settings.EMBEDDING_API_KEY}"},
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        embs = data.get("output", {}).get("embeddings", [])
        return [e.get("embedding", []) for e in embs]
    except Exception:
        return None


def embed_texts(texts: list[str], batch_size: int = 8) -> list[list[float]] | None:
    """批量向量化若干文本；返回与输入等长的向量列表，失败返回 None"""
    if not texts:
        return []
    if not embedding_available():
        return None
    model = settings.EMBEDDING_MODEL
    out: list[list[float] | None] = [None] * len(texts)
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        payload = {"model": model, "input": {"contents": [{"text": t} for t in batch]}}
        embs = _call(payload)
        if embs is not None and len(embs) == len(batch):
            for j, e in enumerate(embs):
                out[i + j] = e
            continue
        # 批量失败 → 逐条重试
        for j, t in enumerate(batch):
            embs = _call({"model": model, "input": {"contents": [{"text": t}]}})
            if embs and embs[0]:
                out[i + j] = embs[0]
    if any(v is None or len(v) == 0 for v in out):
        return None
    return [v for v in out]


def embed_text(text: str) -> list[float] | None:
    r = embed_texts([text])
    return r[0] if r else None
