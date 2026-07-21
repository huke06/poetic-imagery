"""运行时配置存储：后台界面可热修改的系统变量

优先级：runtime_config.json > 环境变量/.env > 代码默认值
- LLM 配置、上游地址修改后即时生效（每次调用时读取）
- runtime_config.json 不纳入版本管理，属于部署私有配置
"""
import json
from pathlib import Path
from typing import Any

RUNTIME_CONFIG_PATH = Path(__file__).resolve().parent.parent / "runtime_config.json"

# 允许后台修改的键（白名单，避免任意写入）
EDITABLE_KEYS = {
    "LLM_API_KEY": {"label": "大模型 API Key", "secret": True, "hint": "OpenAI 兼容协议（豆包/通义千问/OpenAI），留空则智能助手使用本地知识库生成"},
    "LLM_BASE_URL": {"label": "大模型接口地址", "secret": False, "hint": "如 https://api.openai.com/v1 或 https://ark.cn-beijing.volces.com/api/v3"},
    "LLM_MODEL": {"label": "大模型型号", "secret": False, "hint": "如 gpt-4o-mini / doubao-pro-32k / qwen-plus"},
    "UPSTREAM_WRITING_BASE": {"label": "上游诗文库地址", "secret": False, "hint": "默认 https://open.cnkgraph.com"},
    "UPSTREAM_BOOK_BASE": {"label": "上游古籍库地址", "secret": False, "hint": "默认 https://api.cnkgraph.com"},
    "ADMIN_TOKEN": {"label": "管理后台令牌", "secret": True, "hint": "管理接口与后台界面登录用"},
}


def _load() -> dict:
    if RUNTIME_CONFIG_PATH.exists():
        try:
            return json.loads(RUNTIME_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def get(key: str, default: Any = None) -> Any:
    """读取配置：运行时文件优先，缺省回落默认值"""
    return _load().get(key, default)


def get_effective(key: str, env_default: Any) -> Any:
    """运行时文件 > 环境变量默认值"""
    return _load().get(key, env_default)


def all_effective(env_fallback: dict) -> dict:
    """返回所有可编辑键的生效值（secret 键打码）"""
    stored = _load()
    result = []
    for key, meta in EDITABLE_KEYS.items():
        value = stored.get(key, env_fallback.get(key, ""))
        result.append({
            "key": key,
            "label": meta["label"],
            "hint": meta["hint"],
            "secret": meta["secret"],
            "value": ("••••••" + str(value)[-4:]) if meta["secret"] and value else value,
            "is_set": bool(value),
            "source": "runtime" if key in stored else "env",
        })
    return result


def update(changes: dict) -> dict:
    """更新白名单内的键；空字符串表示清除该覆盖（回落 env）"""
    stored = _load()
    for key, value in changes.items():
        if key not in EDITABLE_KEYS:
            continue
        if value == "" or value is None:
            stored.pop(key, None)
        else:
            stored[key] = str(value)
    RUNTIME_CONFIG_PATH.write_text(json.dumps(stored, ensure_ascii=False, indent=2), encoding="utf-8")
    return stored
