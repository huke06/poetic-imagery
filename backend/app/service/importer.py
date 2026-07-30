# -*- coding: utf-8 -*-
"""批量导入服务：JSON / CSV 统一解析、校验与入库（CLI 与后台接口共用）

支持格式：
1. JSON（富格式，功能最全）：单个意象对象 / {"concepts": [...]} / 顶层数组
   结构同 scripts/concept_template.json（concept + poetries + couplets + artworks + relations）
2. CSV-诗文关联（poetries）：一行一条「诗文-意象」关联，列见 sample poetries_sample.csv
3. CSV-意象本体（concepts）：一行一个意象基础信息，列见 sample concepts_sample.csv
   CSV 类型按表头自动识别，无需用户指定
"""
import csv
import io
import json
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import (
    Artwork, Concept, ConceptArtworkRel, ConceptPoetryRel, ConceptRelation,
    Couplet, DynastyStats, Poetry,
)
from ..utils.palette import assign_color

DYNASTY_ORDER = ["先秦", "汉", "魏晋", "唐", "五代", "宋", "元", "明", "清"]


# ═══════════════ 通用工具 ═══════════════
def split_clauses(content: str) -> list[str]:
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


def recompute_stats(db: Session, concept: Concept):
    db.query(DynastyStats).filter_by(concept_id=concept.id).delete()
    counts, seen = {}, set()
    for r in db.query(ConceptPoetryRel).filter_by(concept_id=concept.id).all():
        dyn = r.poetry.dynasty
        if (dyn, r.poetry_id) not in seen:
            seen.add((dyn, r.poetry_id))
            counts[dyn] = counts.get(dyn, 0) + 1
    for dyn in DYNASTY_ORDER:
        if counts.get(dyn):
            db.add(DynastyStats(concept_id=concept.id, dynasty=dyn, count=counts[dyn]))


def _norm_tags(s: str) -> str:
    """情感标签归一化为英文逗号分隔（兼容空格、顿号、中文逗号分隔写法，适配 CSV 单元格）"""
    parts = [p for p in re_split(s) if p]
    return ",".join(parts)


def re_split(s: str) -> list[str]:
    import re
    return [p for p in re.split(r"[,，、\s]+", s or "") if p]


def re_search(name: str) -> bool:
    """是否为模板占位文字"""
    import re
    return bool(re.search(r"必填|意象名|示例|占位|xxx|XXX", name))


# ═══════════════ 校验 ═══════════════
def validate(data: dict) -> tuple[list[str], list[str]]:
    """静态校验（不查库）。返回 (错误列表, 提示列表)"""
    errors, warns = [], []
    c = data.get("concept") or {}
    if not c.get("name"):
        errors.append("concept.name 缺失")
    tags = set(re_split(c.get("emotion_tags", "")))
    names = [c.get("name", "")] + [a for a in (c.get("aliases") or "").split(",") if a]
    for i, p in enumerate(data.get("poetries", [])):
        for f in ("title", "author", "content", "rels"):
            if f not in p:
                errors.append(f"poetries[{i}]《{p.get('title', '?')}》缺少字段 {f}")
        for r in p.get("rels", []):
            if not r.get("clause"):
                errors.append(f"poetries[{i}]《{p.get('title')}》存在空 clause")
            if tags and r.get("emotion") and r.get("emotion") not in tags:
                errors.append(f"poetries[{i}]《{p.get('title')}》情感「{r.get('emotion')}」不在意象标签集 {sorted(tags)} 内")
            if r.get("clause") and not any(n and n in r["clause"] for n in names):
                warns.append(f"poetries[{i}]《{p.get('title')}》诗句「{r['clause'][:12]}…」未直接出现意象词/别称（间接关联，请确认）")
    return errors, warns


def validate_against_db(db: Session, data: dict) -> list[str]:
    """结合库状态的校验：
    - 数据包未提供情感标签时，若意象不存在于库中则报错（新意象必须有标签）
    - 数据包提供了情感标签时，逐条核对关联情感是否越界（新意象按包内标签，已有意象按库内标签）
    """
    errors = []
    c = data.get("concept") or {}
    name = (c.get("name") or "").strip()
    if not name:
        return errors
    # 模板占位符防呆：原样上传未编辑模板时给出明确指引
    if re_search(name):
        errors.append(f"「{name}」看起来是模板占位文字，请先在模板中填写真实意象名再上传")
        return errors
    tags = set(re_split(c.get("emotion_tags", "")))
    existing = db.query(Concept).filter_by(name=name).first()
    if not tags:
        if not existing:
            errors.append(f"「{name}」为新意象，必须提供 emotion_tags（情感标签）")
        return errors
    # 关联情感越界检查（数据包提供了标签才查）
    for p in data.get("poetries", []):
        for r in p.get("rels", []):
            emo = r.get("emotion") if isinstance(r, dict) else r[1]
            if emo and emo not in tags:
                errors.append(f"《{p.get('title')}》情感「{emo}」不在意象「{name}」标签集 {sorted(tags)} 内")
    return errors


# ═══════════════ 入库 ═══════════════
def _norm_rel(r) -> dict:
    """关联标注字段归一化（兼容元组/列表/字典三种写法）"""
    if isinstance(r, dict):
        return {"clause": r.get("clause", ""), "emotion": r.get("emotion", ""),
                "is_classic": int(r.get("is_classic", 0)), "weight": int(r.get("weight", 1)),
                "annotation": r.get("annotation", "")}
    clause, emotion, is_classic, weight = r
    return {"clause": clause, "emotion": emotion, "is_classic": int(is_classic), "weight": int(weight),
            "annotation": r[4] if len(r) > 4 else ""}


def _map_legacy_concept(cdata: dict) -> dict:
    """旧字段 category → category_main + category_sub 自动补齐"""
    from ..utils.palette import LEGACY_CATEGORY_MAP
    if cdata.get("category") and not cdata.get("category_main"):
        main, sub = LEGACY_CATEGORY_MAP.get(cdata["category"], ("自然类", ""))
        cdata["category_main"] = main
        cdata["category_sub"] = sub
    return cdata


def _map_legacy_artwork(a: dict) -> dict:
    a["dynasty_period"] = a.get("dynasty_period") or a.get("dynasty", "")
    if a.get("imgs") and not a.get("image_url"):
        a["image_url"] = a["imgs"]
    return a


def import_concept_data(db: Session, data: dict, with_svg: bool = True) -> dict:
    """导入一个意象数据包，返回统计报告。调用方负责 commit/rollback。"""
    report = {"concept": "", "concept_created": False, "poetry_new": 0, "poetry_reused": 0,
              "rel_new": 0, "rel_skipped": 0, "couplet_new": 0, "artwork_new": 0, "artwork_reused": 0,
              "relation_new": 0, "warnings": []}

    cdata = _map_legacy_concept(data.get("concept", {}))
    name = cdata["name"].strip()
    report["concept"] = name

    concept = db.query(Concept).filter_by(name=name).first()
    if not concept:
        concept = Concept(
            name=name,
            category_main=cdata.get("category_main", "") or "自然类",
            category_sub=cdata.get("category_sub", ""),
            theme_color=cdata.get("theme_color") or assign_color(name, cdata.get("category_main", ""))["color"],
            aliases=cdata.get("aliases", ""),
            original_meaning=cdata.get("original_meaning", ""),
            poetic_meaning=cdata.get("poetic_meaning", ""),
            emotion_tags=_norm_tags(cdata.get("emotion_tags", "")),
            origin_dynasty=cdata.get("origin_dynasty", ""),
            peak_dynasty=cdata.get("peak_dynasty", ""),
            description=cdata.get("description", ""),
        )
        db.add(concept)
        db.flush()
        report["concept_created"] = True
    else:
        # 已存在时补充缺失的描述类字段（不覆盖已有内容）
        for f in ("aliases", "original_meaning", "poetic_meaning", "origin_dynasty", "peak_dynasty", "description",
                  "category_main", "category_sub"):
            if cdata.get(f) and (not getattr(concept, f, None) or (f in ("category_main", "category_sub") and not getattr(concept, f, None))):
                if f == "category_main" and not concept.category_main:
                    concept.category_main = cdata[f]
                elif f == "category_sub" and not concept.category_sub:
                    concept.category_sub = cdata[f]
                elif f not in ("category_main", "category_sub"):
                    if not getattr(concept, f, None):
                        setattr(concept, f, cdata[f])

    # 诗文与关联
    for p in data.get("poetries", []):
        poetry = db.query(Poetry).filter_by(title=p["title"], author=p.get("author", "佚名")).first()
        if poetry:
            report["poetry_reused"] += 1
        else:
            poetry = Poetry(
                title=p["title"], author=p.get("author", "佚名"), dynasty=p.get("dynasty", ""),
                writing_type=p.get("writing_type", "诗"), content=p["content"],
                clauses=json.dumps(split_clauses(p["content"]), ensure_ascii=False),
            )
            db.add(poetry)
            db.flush()
            report["poetry_new"] += 1
        for raw in p.get("rels", []):
            r = _norm_rel(raw)
            if not r["clause"]:
                continue
            dup = db.query(ConceptPoetryRel).filter_by(
                concept_id=concept.id, poetry_id=poetry.id, clause=r["clause"]).first()
            if dup:
                report["rel_skipped"] += 1
                continue
            db.add(ConceptPoetryRel(concept_id=concept.id, poetry_id=poetry.id, **r))
            report["rel_new"] += 1

    # 对仗
    for cp in data.get("couplets", []):
        if isinstance(cp, dict):
            word_a, word_b, verse, source = cp.get("word_a", ""), cp.get("word_b", ""), cp.get("verse", ""), cp.get("source", "")
        else:
            word_a, word_b, verse, source = cp
        if verse and not db.query(Couplet).filter_by(concept_id=concept.id, verse=verse).first():
            db.add(Couplet(concept_id=concept.id, word_a=word_a, word_b=word_b, verse=verse, source=source))
            report["couplet_new"] += 1

    # 古画
    artworks = data.get("artworks", [])
    if artworks:
        need_svg = [a for a in artworks
                    if not db.query(Artwork).filter_by(name=a["name"], artist=a.get("artist", "佚名")).first()]
        svg_files: list[str] = []
        if with_svg and need_svg:
            import sys
            backend_root = Path(__file__).resolve().parent.parent.parent
            if str(backend_root) not in sys.path:
                sys.path.insert(0, str(backend_root))
            from scripts.svg_art import ensure_artwork_svgs
            svg_dir = backend_root / "app" / "static" / "artworks"
            svg_files = ensure_artwork_svgs(need_svg, svg_dir)
        svg_iter = iter(svg_files)
        for a in artworks:
            artwork = db.query(Artwork).filter_by(name=a["name"], artist=a.get("artist", "佚名")).first()
            if artwork:
                report["artwork_reused"] += 1
                # 旧数据回填 dynasty_period
                if not artwork.dynasty_period and artwork.dynasty:
                    artwork.dynasty_period = artwork.dynasty
            else:
                _map_legacy_artwork(a)
                fallback = f"/static/artworks/{next(svg_iter)}" if svg_files else ""
                artwork = Artwork(
                    name=a["name"], artist=a.get("artist", "佚名"), dynasty_period=a.get("dynasty_period", ""),
                    material=a.get("material", ""), size=a.get("size", ""),
                    subject_names=a.get("subject_names", ""),
                    image_url=a.get("image_url") or fallback, thumb_url=a.get("thumb_url") or fallback,
                    description=a.get("description", ""),
                )
                db.add(artwork)
                db.flush()
                report["artwork_new"] += 1
            if not db.query(ConceptArtworkRel).filter_by(concept_id=concept.id, artwork_id=artwork.id).first():
                db.add(ConceptArtworkRel(concept_id=concept.id, artwork_id=artwork.id,
                                         relation_desc=a.get("relation_desc", ""), weight=int(a.get("weight", 1))))

    # 意象-意象关联
    for rel in data.get("relations", []):
        if isinstance(rel, dict):
            to_name, rtype, desc = rel.get("to", ""), rel.get("relation_type", ""), rel.get("description", "")
        else:
            to_name, rtype, desc = rel
        target = db.query(Concept).filter_by(name=to_name).first()
        if not target:
            report["warnings"].append(f"关联目标意象「{to_name}」不存在，已跳过")
            continue
        if not db.query(ConceptRelation).filter_by(from_concept_id=concept.id, to_concept_id=target.id).first():
            db.add(ConceptRelation(from_concept_id=concept.id, to_concept_id=target.id,
                                   relation_type=rtype, description=desc))
            report["relation_new"] += 1

    recompute_stats(db, concept)
    # 自动预生成新诗的翻译与赏析（有 LLM 时）
    if report["poetry_new"] > 0 and with_svg:
        try:
            from ..api.poetry import pregenerate_for_poem
            for p in data.get("poetries", []):
                poetry = db.query(Poetry).filter_by(title=p["title"], author=p.get("author", "佚名")).first()
                if poetry and (not poetry.translation or not poetry.appreciation):
                    pregenerate_for_poem(db, poetry)
        except Exception:
            pass
    return report


# ═══════════════ 格式解析 ═══════════════
def parse_json(text: str) -> list[dict]:
    """JSON → 意象数据包列表"""
    obj = json.loads(text)
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict) and "concepts" in obj:
        return obj["concepts"]
    return [obj]


def _unescape_newlines(s: str) -> str:
    """CSV 单元格中的字面 \\n 还原为真换行"""
    return (s or "").replace("\\n", "\n")


def parse_csv(text: str) -> tuple[str, list[dict] | None, list[str]]:
    """按表头自动识别 CSV 类型，返回 (类型, 意象数据包列表或本体行列表, 错误列表)

    类型：'poetries'（诗文关联）/ 'concepts'（意象本体）
    """
    errors: list[str] = []
    reader = csv.DictReader(io.StringIO(text))
    headers = set(reader.fieldnames or [])

    if {"name", "emotion_tags"} <= headers:
        # ── 意象本体表 ──
        packs = []
        for i, row in enumerate(reader, start=2):
            if not (row.get("name") or "").strip():
                continue
            packs.append({"concept": {
                "name": row["name"].strip(),
                "category": (row.get("category") or "").strip(),   # 旧字段兜底
                "category_main": (row.get("category_main") or row.get("category") or "").strip(),
                "category_sub": (row.get("category_sub") or "").strip(),
                "aliases": (row.get("aliases") or "").strip(),
                "emotion_tags": (row.get("emotion_tags") or "").strip(),
                "origin_dynasty": (row.get("origin_dynasty") or "").strip(),
                "peak_dynasty": (row.get("peak_dynasty") or "").strip(),
                "theme_color": (row.get("theme_color") or "").strip(),
                "original_meaning": (row.get("original_meaning") or "").strip(),
                "poetic_meaning": (row.get("poetic_meaning") or "").strip(),
                "description": _unescape_newlines((row.get("description") or "").strip()),
            }, "poetries": [], "couplets": [], "artworks": [], "relations": []})
        return "concepts", packs, errors

    if {"concept_name", "title", "clause"} <= headers:
        # ── 诗文关联表：按意象聚合 ──
        packs_map: dict[str, dict] = {}
        for i, row in enumerate(reader, start=2):
            cname = (row.get("concept_name") or "").strip()
            title = (row.get("title") or "").strip()
            if not cname or not title:
                errors.append(f"第 {i} 行：concept_name 与 title 不能为空")
                continue
            # 新字段 category_main/category_sub 兼容旧字段 concept_category
            cm = (row.get("category_main") or row.get("concept_category") or "").strip()
            cs = (row.get("category_sub") or "").strip()
            tags = (row.get("concept_tags") or "").strip()
            pack = packs_map.setdefault(cname, {
                "concept": {"name": cname, "category_main": cm, "category_sub": cs,
                            "emotion_tags": tags},
                "poetries_map": {}, "couplets": [], "artworks": [], "relations": []})
            if not pack["concept"].get("category_main") and cm:
                pack["concept"]["category_main"] = cm
            if not pack["concept"].get("category_sub") and cs:
                pack["concept"]["category_sub"] = cs
            if not pack["concept"].get("emotion_tags") and tags:
                pack["concept"]["emotion_tags"] = tags

            key = (title, (row.get("author") or "佚名").strip())
            pm = pack["poetries_map"]
            if key not in pm:
                pm[key] = {"title": title, "author": key[1],
                           "dynasty": (row.get("dynasty") or "").strip(),
                           "writing_type": (row.get("writing_type") or "诗").strip(),
                           "content": _unescape_newlines((row.get("content") or "").strip()),
                           "rels": []}
            clause = (row.get("clause") or "").strip()
            if clause:
                pm[key]["rels"].append({
                    "clause": clause,
                    "emotion": (row.get("emotion") or "").strip(),
                    "is_classic": 1 if (row.get("is_classic") or "").strip() in ("1", "是", "true", "TRUE") else 0,
                    "weight": int((row.get("weight") or "1").strip() or 1),
                })
        packs = []
        for pack in packs_map.values():
            pack["poetries"] = list(pack.pop("poetries_map").values())
            packs.append(pack)
        return "poetries", packs, errors

    return "", None, [f"无法识别的 CSV 表头：{sorted(headers)}。"
                      "诗文关联表需含 concept_name,title,clause；意象本体表需含 name,emotion_tags"]


def build_import_preview(packs: list[dict], fmt: str) -> dict:
    """dry-run 汇总"""
    return {
        "format": fmt,
        "concept_count": len(packs),
        "concepts": [p["concept"]["name"] for p in packs],
        "poetry_rows": sum(len(p.get("poetries", [])) for p in packs),
        "rel_rows": sum(len(pp.get("rels", [])) for p in packs for pp in p.get("poetries", [])),
        "couplet_rows": sum(len(p.get("couplets", [])) for p in packs),
        "artwork_rows": sum(len(p.get("artworks", [])) for p in packs),
    }
