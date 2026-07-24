"""全局配置：支持通过 .env / 环境变量覆盖"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    # 数据库（默认项目内 SQLite 单文件）
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'shixiangzhi.db'}")

    # 上游开放数据接口（诗文库，可选；未配置或不可用时自动回退本地数据）
    UPSTREAM_WRITING_BASE: str = os.getenv("UPSTREAM_WRITING_BASE", "https://open.cnkgraph.com")
    UPSTREAM_BOOK_BASE: str = os.getenv("UPSTREAM_BOOK_BASE", "https://api.cnkgraph.com")
    UPSTREAM_TIMEOUT: float = float(os.getenv("UPSTREAM_TIMEOUT", "8"))

    # 大模型（可选；未配置时智能助手自动使用本地知识库生成）
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-v4-flash")

    # 管理后台令牌
    ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "shixiangzhi-admin")

    # 服务
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))


settings = Settings()
