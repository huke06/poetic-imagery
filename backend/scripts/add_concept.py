# -*- coding: utf-8 -*-
"""意象增量导入工具（CLI）：不删库，向现有知识库中追加意象

用法：
    python scripts/add_concept.py <concept.json>        # 导入 JSON（单意象/多意象均可）
    python scripts/add_concept.py <file.csv>            # 导入 CSV（按表头自动识别类型）
    python scripts/add_concept.py --check <file>        # 仅校验不落库
    python scripts/add_concept.py --delete 柳           # 删除某意象（诗文保留，关联级联删除）

模板：scripts/concept_template.json、scripts/examples/*.csv（与后台「批量导入」模板一致）
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from app.database import SessionLocal, init_db  # noqa: E402
from app.models import Concept, ConceptPoetryRel  # noqa: E402
from app.service import importer  # noqa: E402


def delete_concept(name: str) -> None:
    db = SessionLocal()
    try:
        concept = db.query(Concept).filter_by(name=name).first()
        if not concept:
            print(f"意象「{name}」不存在")
            return
        n_rel = db.query(ConceptPoetryRel).filter_by(concept_id=concept.id).count()
        db.delete(concept)  # 关联/对仗/统计级联删除，诗文与古画本体保留
        db.commit()
        print(f"✓ 已删除意象「{name}」及其 {n_rel} 条诗文关联（诗文本体保留）")
    finally:
        db.close()


def main() -> None:
    init_db()
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)
    if args[0] == "--delete":
        delete_concept(args[1])
        sys.exit(0)

    check_only = args[0] == "--check"
    path = Path(args[-1])
    text = path.read_text(encoding="utf-8-sig")

    if path.suffix.lower() == ".json":
        packs = importer.parse_json(text)
        fmt = "json"
    elif path.suffix.lower() == ".csv":
        fmt, packs, errs = importer.parse_csv(text)
        if packs is None:
            for e in errs:
                print(e)
            sys.exit(1)
        fmt = f"csv-{fmt}"
    else:
        print("仅支持 .json 或 .csv")
        sys.exit(1)

    errors, warns = [], []
    for pack in packs:
        e, w = importer.validate(pack)
        errors += e
        warns += w
    db = SessionLocal()
    try:
        for pack in packs:
            errors += importer.validate_against_db(db, pack)
    finally:
        db.close()
    for w in warns:
        print(f"[提示] {w}")
    if errors:
        for e in errors:
            print(f"[错误] {e}")
        print(f"\n校验未通过：{len(errors)} 处错误")
        sys.exit(1)

    preview = importer.build_import_preview(packs, fmt)
    print(f"格式 {preview['format']}｜意象 {preview['concept_count']} 个 {preview['concepts']}｜"
          f"诗文 {preview['poetry_rows']} 首｜关联 {preview['rel_rows']} 条")
    if check_only:
        print(f"\n校验通过（{len(warns)} 条提示），未执行导入")
        sys.exit(0)

    db = SessionLocal()
    try:
        for pack in packs:
            r = importer.import_concept_data(db, pack)
            status = "新建" if r["concept_created"] else "补充"
            print(f"✓ [{status}]「{r['concept']}」：诗文 新增{r['poetry_new']}/复用{r['poetry_reused']}，"
                  f"关联 {r['rel_new']} 条（跳过重复 {r['rel_skipped']}），"
                  f"对仗 {r['couplet_new']}，古画 新增{r['artwork_new']}/复用{r['artwork_reused']}，意象关联 {r['relation_new']}")
            for w in r["warnings"]:
                print(f"  [提示] {w}")
        db.commit()
        print("\n导入完成 ✔  前端页面、图表、问答、创诗均已自动生效")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
