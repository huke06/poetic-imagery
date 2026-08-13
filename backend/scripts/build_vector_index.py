# -*- coding: utf-8 -*-
"""构建 / 重建向量索引

用法：
    python scripts/build_vector_index.py          # 若为空则构建
    python scripts/build_vector_index.py --force  # 强制重建
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from app.database import SessionLocal
from app.service import embedding_index


def main():
    force = "--force" in sys.argv
    db = SessionLocal()
    try:
        result = embedding_index.build_index(db, force=force)
        print("向量索引状态:", result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
