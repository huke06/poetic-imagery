# -*- coding: utf-8 -*-
"""数据库初始化与种子数据导入

用法：
    python scripts/seed.py            # 建库 + 导入种子数据（会先清空旧数据）
    python scripts/seed.py --keep     # 仅当库为空时导入
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")  # Windows 控制台兼容

from app.database import SessionLocal, init_db  # noqa: E402
from app.models import (  # noqa: E402
    Artwork, Concept, ConceptArtworkRel, ConceptPoetryRel, ConceptRelation,
    Couplet, DynastyStats, Poetry,
)
from scripts.seed_data import (  # noqa: E402
    ARTWORKS, CONCEPT_RELATIONS, CONCEPTS, COUPLETS, DYNASTY_ORDER, POETRIES,
)
from scripts.svg_art import ensure_artwork_svgs  # noqa: E402


def split_clauses(content: str) -> list[str]:
    """将全文按标点切成句读，供诗文详情页逐句渲染与高亮"""
    clauses, buf = [], ""
    for ch in content:
        buf += ch
        if ch in "。！？；\n":
            c = buf.strip(" \n")
            if c:
                clauses.append(c)
            buf = ""
    if buf.strip():
        clauses.append(buf.strip())
    return clauses


def _normalize_concept(c: dict) -> dict:
    """旧 category → 新 category_main + category_sub 自动映射"""
    from app.utils.palette import LEGACY_CATEGORY_MAP, SUB_CATEGORIES
    c = dict(c)
    if c.get("category") and not c.get("category_main"):
        main, sub = LEGACY_CATEGORY_MAP.get(c["category"], ("自然类", ""))
        c["category_main"] = main
        c["category_sub"] = sub
    return c


def _normalize_artwork(a: dict) -> dict:
    a = dict(a)
    if not a.get("dynasty_period"):
        a["dynasty_period"] = a.get("dynasty", "")
    if a.get("imgs") and not a.get("image_url"):
        a["image_url"] = a["imgs"]
    return a


def run(keep: bool = False):
    init_db()
    db = SessionLocal()
    try:
        if keep and db.query(Concept).count() > 0:
            print("数据库非空，跳过导入（--keep）")
            return

        # 清空旧数据（按外键依赖顺序）
        for t in (ConceptPoetryRel, ConceptArtworkRel, ConceptRelation, DynastyStats, Couplet, Artwork, Poetry, Concept):
            db.query(t).delete()
        db.commit()

        # 1. 意象
        concept_map = {}
        for c in CONCEPTS:
            c = _normalize_concept(c)
            obj = Concept(**c)
            db.add(obj)
            db.flush()
            concept_map[c["name"]] = obj
        print(f"✓ 意象 {len(concept_map)} 条")

        # 2. 诗文 + 意象-诗文关联
        poetry_count, rel_count = 0, 0
        for p in POETRIES:
            rels = p.pop("rels")
            obj = Poetry(**p, clauses=json.dumps(split_clauses(p["content"]), ensure_ascii=False))
            db.add(obj)
            db.flush()
            poetry_count += 1
            for cname, items in rels.items():
                for clause, emotion, is_classic, weight in items:
                    db.add(ConceptPoetryRel(
                        concept_id=concept_map[cname].id, poetry_id=obj.id,
                        clause=clause, emotion=emotion, is_classic=is_classic, weight=weight,
                    ))
                    rel_count += 1
        print(f"✓ 诗文 {poetry_count} 首，意象关联 {rel_count} 条")

        # 3. 古画 + 意象-古画关联（同时生成本地 SVG 画作占位图）
        svg_dir = Path(__file__).resolve().parent.parent / "app" / "static" / "artworks"
        svg_files = ensure_artwork_svgs(ARTWORKS, svg_dir)
        art_count = 0
        for i, a in enumerate(ARTWORKS):
            cname = a.pop("concept")
            relation_desc = a.pop("relation_desc")
            weight = a.pop("weight")
            a.pop("collection", None)  # 藏馆信息并入描述
            a_clean = _normalize_artwork(a)
            svg_rel = f"/static/artworks/{svg_files[i]}"
            obj = Artwork(**a_clean, image_url=svg_rel, thumb_url=svg_rel)
            db.add(obj)
            db.flush()
            art_count += 1
            db.add(ConceptArtworkRel(
                concept_id=concept_map[cname].id, artwork_id=obj.id,
                relation_desc=relation_desc, weight=weight,
            ))
        print(f"✓ 古画 {art_count} 幅（本地 SVG 图像已生成于 {svg_dir}）")

        # 4. 意象-意象关联
        for from_name, to_name, rtype, desc in CONCEPT_RELATIONS:
            db.add(ConceptRelation(
                from_concept_id=concept_map[from_name].id,
                to_concept_id=concept_map[to_name].id,
                relation_type=rtype, description=desc,
            ))
        print(f"✓ 意象关联 {len(CONCEPT_RELATIONS)} 条")

        # 5. 对仗词组
        couplet_count = 0
        for cname, items in COUPLETS.items():
            for word_a, word_b, verse, source in items:
                db.add(Couplet(concept_id=concept_map[cname].id, word_a=word_a, word_b=word_b, verse=verse, source=source))
                couplet_count += 1
        print(f"✓ 对仗词组 {couplet_count} 组")

        # 6. 朝代统计（依据真实关联数据自动计算）
        stat_count = 0
        for cname, concept in concept_map.items():
            counts: dict[str, int] = {}
            seen: set[tuple[str, int]] = set()  # 同一首诗在同一朝代只计一次
            rels = db.query(ConceptPoetryRel).filter_by(concept_id=concept.id).all()
            for r in rels:
                dyn = r.poetry.dynasty
                if (dyn, r.poetry_id) not in seen:
                    seen.add((dyn, r.poetry_id))
                    counts[dyn] = counts.get(dyn, 0) + 1
            for dyn in DYNASTY_ORDER:
                if counts.get(dyn):
                    db.add(DynastyStats(concept_id=concept.id, dynasty=dyn, count=counts[dyn]))
                    stat_count += 1
        print(f"✓ 朝代统计 {stat_count} 条（自动计算）")

        db.commit()
        print("\n种子数据导入完成 ✔")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run(keep="--keep" in sys.argv)
