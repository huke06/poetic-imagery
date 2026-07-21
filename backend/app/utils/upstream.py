"""上游开放接口客户端（诗文库/古籍库，可选）

- 基础地址可在 .env 中配置（UPSTREAM_WRITING_BASE / UPSTREAM_BOOK_BASE）
- 所有调用均带超时与异常兜底：上游不可用时返回 None，由业务层回退本地数据
"""
import httpx

from .. import config_store
from ..config import settings


def _base(which: str) -> str:
    if which == "book":
        return config_store.get_effective("UPSTREAM_BOOK_BASE", settings.UPSTREAM_BOOK_BASE)
    return config_store.get_effective("UPSTREAM_WRITING_BASE", settings.UPSTREAM_WRITING_BASE)


def _get(base: str, path: str, **params) -> dict | None:
    try:
        resp = httpx.get(f"{base.rstrip('/')}/{path.lstrip('/')}", params=params, timeout=settings.UPSTREAM_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def writing_detail(writing_id: str) -> dict | None:
    return _get(_base("writing"), f"/api/writing/{writing_id}")


def writing_tones(writing_id: str) -> dict | None:
    return _get(_base("writing"), f"/api/writing/{writing_id}/tones")


def writing_book_links(writing_id: str) -> dict | None:
    return _get(_base("writing"), f"/api/writing/{writing_id}/bookLinks")


def writing_labelize(writing_id: str) -> dict | None:
    return _get(_base("writing"), f"/api/writing/{writing_id}/labelize")


def similar_clauses(key: str) -> dict | None:
    return _get(_base("writing"), f"/api/writing/SimilarClauses/{key}")


def same_rhymes(key: str) -> dict | None:
    return _get(_base("writing"), f"/api/writing/SameRhymes/{key}")
