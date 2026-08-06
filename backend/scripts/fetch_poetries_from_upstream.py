"""从 cnkgraph 上游拉取意象关联诗句，自动入库 + LLM 角色分析

用法：限流解除后执行一次——
  cd backend && python scripts/fetch_poetries_from_upstream.py
"""
import sys, time
sys.path.insert(0, ".")

from app.database import SessionLocal
from app.models import Concept, ConceptPoetryRel, Poetry
from app.utils.upstream import similar_clauses
from app.utils.llm import llm_available
from app.api.concept import analyze_roles_for_concept

PER_CONCEPT = 15      # 每个意象拉取诗句数
SLEEP_SEC = 1.0       # API 请求间隔


def main():
    db = SessionLocal()
    concepts = db.query(Concept).all()
    total_new = 0

    for c in concepts:
        print(f"\n[{c.name}] 拉取中…", end=" ", flush=True)
        result = similar_clauses(c.name)
        if not result:
            print("上游无数据")
            continue

        # similar_clauses 返回结构: {clauses: [...], ...} 或直接是列表
        clauses = result if isinstance(result, list) else result.get("clauses", result.get("data", []))
        if not clauses:
            print("格式异常")
            continue

        added = 0
        for item in clauses[:PER_CONCEPT * 2]:  # 多拉一些，去重
            # 解析诗句（格式因接口版本而异，做兼容）
            if isinstance(item, str):
                clause = item
                title = author = dynasty = ""
            elif isinstance(item, dict):
                clause = item.get("clause") or item.get("sentence") or ""
                title = item.get("title") or item.get("poetryTitle") or ""
                author = item.get("author") or item.get("poet") or "佚名"
                dynasty = item.get("dynasty") or ""
            else:
                continue

            if not clause or c.name not in clause:
                continue

            # 去重：检查是否已有相同 clause
            exists = db.query(ConceptPoetryRel).filter_by(
                concept_id=c.id, clause=clause,
            ).first()
            if exists:
                continue

            # 创建或复用 Poetry
            poetry = None
            if title and author:
                poetry = db.query(Poetry).filter_by(title=title, author=author).first()
            if not poetry:
                poetry = Poetry(title=title or f"上游佚题_{c.name}", author=author or "佚名",
                                dynasty=dynasty or "", writing_type="诗", content=clause)
                db.add(poetry)
                db.flush()

            db.add(ConceptPoetryRel(concept_id=c.id, poetry_id=poetry.id,
                                    clause=clause, weight=1, is_classic=0))
            added += 1
            total_new += 1
            if added >= PER_CONCEPT:
                break

        db.commit()
        print(f"+{added} 条")

        time.sleep(SLEEP_SEC)

    print(f"\n总计新增 {total_new} 条关联。")

    # LLM 角色分析
    if llm_available() and total_new > 0:
        print("开始 LLM 角色分析…")
        for c in concepts:
            n = analyze_roles_for_concept(db, c.id)
            if n: print(f"  {c.name}: +{n}")
        db.commit()

    db.close()
    print("完成。")


if __name__ == "__main__":
    main()
