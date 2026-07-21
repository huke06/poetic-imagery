# -*- coding: utf-8 -*-
"""一键重建知识库：种子数据（月/夕阳）+ 全部示例增量包（柳/雁及其补充）

新克隆仓库后执行：
    python scripts/rebuild_all.py
即可完整复现演示数据库（db 文件已 gitignore，不在仓库中）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from app.database import SessionLocal  # noqa: E402
from app.service import importer  # noqa: E402
from scripts.seed import run as seed_run  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent / "examples"

# 顺序即依赖：先建概念骨架，再补关联内容
IMPORT_FILES = [
    EXAMPLES / "concept_liu.json",        # 柳（JSON 全量）
    EXAMPLES / "concepts_sample.csv",     # 雁（本体骨架）
    EXAMPLES / "poetries_sample.csv",     # 雁（诗文关联）
    EXAMPLES / "concept_yan_extra.json",  # 雁（补充：对仗/古画/关联）
]


def main():
    print("═══ 第一步：种子数据（月 / 夕阳）═══")
    seed_run()

    print("\n═══ 第二步：增量示例（柳 / 雁）═══")
    db = SessionLocal()
    try:
        for f in IMPORT_FILES:
            if not f.exists():
                print(f"[跳过] {f.name} 不存在")
                continue
            text = f.read_text(encoding="utf-8-sig")
            if f.suffix == ".json":
                packs = importer.parse_json(text)
            else:
                _, packs, errs = importer.parse_csv(text)
                if packs is None:
                    print(f"[失败] {f.name}: {errs}")
                    continue
            for pack in packs:
                errors = importer.validate_against_db(db, pack)
                if errors:
                    print(f"[校验失败] {f.name}: {errors}")
                    continue
                r = importer.import_concept_data(db, pack)
                print(f"✓ {f.name} → 「{r['concept']}」：诗文+{r['poetry_new']} 关联+{r['rel_new']} "
                      f"对仗+{r['couplet_new']} 古画+{r['artwork_new']} 关系+{r['relation_new']}")
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print("\n知识库重建完成 ✔  启动后端：.venv/Scripts/python run.py")


if __name__ == "__main__":
    main()
