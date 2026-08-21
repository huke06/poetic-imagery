# -*- coding: utf-8 -*-
"""一次性数据回填：为缺少 weight=3「代表名句」的意象，从现有诗文语料自动匹配补一条关联。

用法：
    python scripts/backfill_verses.py          # 预览，不写入
    python scripts/backfill_verses.py --apply  # 实际写入数据库
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")  # Windows 控制台兼容

from app.database import SessionLocal, init_db  # noqa: E402
from app.models import Concept, ConceptPoetryRel, Poetry  # noqa: E402

# 仅匹配名字 >=2 字的意象（单字意象极易误匹配，跳过，交前端「空则隐藏」兜底）
MIN_NAME_LEN = 2
# 代表句最长不超过 32 字（更长的多为赋/散文片段，不适合做「名句」）
MAX_CLAUSE_LEN = 32

# 去除句首说话人标注，如「（谢朗）未若柳絮因风起。」→「未若柳絮因风起。」
_PAREN_TAG = re.compile(r"^[（(][^（）()]*[）)]\s*")


def clauses_of(poetry: Poetry) -> list[str]:
    """取诗文分句；clauses 为 JSON 数组，失败时退化为按标点切 content。"""
    try:
        arr = json.loads(poetry.clauses or "[]")
        if isinstance(arr, list):
            return [clean(s) for s in arr if clean(s)]
    except Exception:
        pass
    buf, out = [], ""
    for ch in (poetry.content or ""):
        buf += ch
        if ch in "。！？；\n":
            c = clean(buf)
            if c:
                out.append(c)
            buf = ""
    if clean(buf):
        out.append(clean(buf))
    return out


def clean(s: str) -> str:
    return _PAREN_TAG.sub("", s.strip()).strip()


def score_clause(clause: str, name: str) -> int:
    """给候选句打分：偏好 5~16 字的完整诗句、且意象名只出现一次。"""
    n = len(clause)
    s = 0
    if 5 <= n <= 16:
        s += 20
    elif 4 <= n <= 30:
        s += 10
    if clause.rstrip().endswith(("。", "！", "？")):
        s += 8
    if clause.count(name) == 1:
        s += 3
    s -= max(0, n - 16)  # 超长轻微扣分
    return s


def main():
    init_db()
    db = SessionLocal()
    try:
        # 缺少 weight>=3 代表句的意象（含完全无关联、以及仅有 weight<3 者）
        concepts = (
            db.query(Concept)
            .filter(Concept.category_sub != "桥接词")
            .filter(~Concept.poetry_rels.any(ConceptPoetryRel.weight >= 3))
            .order_by(Concept.id)
            .all()
        )
        poems = db.query(Poetry).order_by(Poetry.id).all()
        corpus = [(p.id, clauses_of(p)) for p in poems]

        matches = []  # (concept, poetry_id, clause, score)
        for c in concepts:
            name = c.name
            if len(name) < MIN_NAME_LEN:
                continue
            best = None
            for pid, clauses in corpus:
                for cl in clauses:
                    if name in cl and len(cl) <= MAX_CLAUSE_LEN:
                        sc = score_clause(cl, name)
                        if best is None or sc > best[3] or (sc == best[3] and pid < best[1]):
                            best = (c, pid, cl, sc)
            if best:
                matches.append(best)

        apply_mode = "--apply" in sys.argv
        print(f"缺 weight>=3 代表句的意象：{len(concepts)} 个")
        print(f"其中多字且语料命中：{len(matches)} 个；单字/未命中：{len(concepts) - len(matches)} 个")
        print(f"模式：{'写入' if apply_mode else '预览（加 --apply 实际写入）'}")
        print("-" * 60)

        new_count = 0
        promoted_count = 0
        for c, pid, clause, sc in matches:
            dup = db.query(ConceptPoetryRel).filter_by(
                concept_id=c.id, poetry_id=pid, clause=clause).first()
            if dup:
                # 同句已存在但权重不足：直接提升为 weight=3 代表句
                if dup.weight < 3:
                    if apply_mode:
                        dup.weight = 3
                        dup.is_classic = 1
                    promoted_count += 1
                    print(f"[提升] {c.name}：「{clause}」 weight→3")
                else:
                    print(f"[跳过已存在] {c.name}：「{clause}」")
                continue
            if apply_mode:
                db.add(ConceptPoetryRel(
                    concept_id=c.id, poetry_id=pid, clause=clause,
                    weight=3, is_classic=1, emotion="", emotion_main="",
                ))
            new_count += 1
            print(f"[{c.name}]  {clause}")

        print("-" * 60)
        if apply_mode:
            db.commit()
            print(f"✓ 已写入 {new_count} 条、提升 {promoted_count} 条 weight=3 代表句关联")
        else:
            print(f"（预览）将写入 {new_count} 条、提升 {promoted_count} 条；确认无误后加 --apply 执行")
    finally:
        db.close()


if __name__ == "__main__":
    main()
