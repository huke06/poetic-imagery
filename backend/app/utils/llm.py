"""可选大模型客户端：OpenAI 兼容协议（豆包/通义千问/OpenAI 均可配置）

配置来源优先级：后台运行时配置（管理界面修改，即时生效）> 环境变量 > 默认。
未配置 LLM_API_KEY 时 chat() 返回 None，智能助手自动回退本地知识库生成。
"""
import httpx

from .. import config_store
from ..config import settings


def _conf():
    return (
        config_store.get_effective("LLM_API_KEY", settings.LLM_API_KEY),
        config_store.get_effective("LLM_BASE_URL", settings.LLM_BASE_URL),
        config_store.get_effective("LLM_MODEL", settings.LLM_MODEL),
    )


def llm_available() -> bool:
    api_key, _, _ = _conf()
    return bool(api_key)


def chat(messages: list[dict], temperature: float = 0.7, timeout: float = 30) -> str | None:
    """调用 OpenAI 兼容的 chat/completions 接口；失败返回 None"""
    api_key, base_url, model = _conf()
    if not api_key:
        return None
    try:
        resp = httpx.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "temperature": temperature},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return None
