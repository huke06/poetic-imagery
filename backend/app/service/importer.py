# -*- coding: utf-8 -*-
"""批量导入服务：JSON / CSV 统一解析、校验与入库（CLI 与后台接口共用）

支持格式：
1. JSON（富格式，功能最全）：单个意象对象 / {"concepts": [...]} / 顶层数组
   结构同 scripts/concept_template.json（concept + poetries + couplets + artworks + relations）
2. CSV-诗文关联（poetries）：一行一条「诗文-意象」关联，列见 sample poetries_sample.csv
3. CSV-意象本体（concepts）：一行一个意象基础信息，列见 sample concepts_sample.csv
4. CSV-对仗（couplets）：word_a / word_b / verse / poet / title
5. CSV-共现（cooccurrence）：name / to / cooccurrence_type / NPMI / diaphaneity / verse / description
   兼容共现分析结果表（word_a / word_b / same_sentence… / NPMI… / transparency…）
6. CSV-情感标签占比统计（emotion_stats）：imagery_emotion_statistics_aggregated.csv
7. CSV-朝代出现频次统计（dynasty_stats）：dynasty_occurrence.csv
   CSV 类型按表头自动识别，无需用户指定
"""
import csv
import io
import json
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import (
    Artwork, Concept, ConceptArtworkRel, ConceptPoetryRel, ConceptRelation,
    Couplet, CooccurrenceStat, DynastyOccurrenceStat, DynastyStats, EmotionStat, Poetry,
)
from ..utils.palette import assign_color
from ..utils.taxonomy import (
    dominant_cooccurrence_type, dynasty_group_of, emotion_main_of,
    normalize_artwork_dynasty, normalize_subjects, rebuild_learned_map_from_db,
)

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
    - 数据包未提供情感标签时不做强校验（emotion_tags 选填）
    - 数据包提供了情感标签时，逐条核对关联情感是否越界
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
    if not tags:
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
        # 桥接词强制升级：导入表中出现的意象不能保持桥接词状态
        is_bridge = (concept.category_sub == "桥接词")
        if is_bridge:
            concept.category_sub = cdata.get("category_sub") or "自然类"
            if concept.category_main == "" or concept.category_main == "自然类":
                concept.category_main = cdata.get("category_main") or "自然类"
            concept.theme_color = cdata.get("theme_color") or assign_color(concept.name, concept.category_main)["color"]
            if cdata.get("emotion_tags"):
                concept.emotion_tags = _norm_tags(cdata["emotion_tags"])
        # 已存在时补充缺失的描述类字段（不覆盖已有内容）
        for f in ("aliases", "original_meaning", "poetic_meaning", "origin_dynasty", "peak_dynasty", "description",
                  "category_main", "category_sub"):
            if cdata.get(f) and not getattr(concept, f, None):
                if f == "emotion_tags":
                    concept.emotion_tags = _norm_tags(cdata[f])
                elif f == "category_sub":
                    if not concept.category_sub or concept.category_sub == "桥接词":
                        concept.category_sub = cdata[f]
                elif f == "category_main":
                    if not concept.category_main:
                        concept.category_main = cdata[f]
                else:
                    setattr(concept, f, cdata[f])
        # emotion_tags 允许直接覆盖（导入表为准）
        if cdata.get("emotion_tags"):
            concept.emotion_tags = _norm_tags(cdata["emotion_tags"])

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
                translation=(p.get("translation") or "").strip(),
                appreciation=(p.get("appreciation") or "").strip(),
            )
            db.add(poetry)
            db.flush()
            report["poetry_new"] += 1
        # 数据包提供了人工翻译/赏析时覆盖写入（留空不动已有缓存）
        if (p.get("translation") or "").strip():
            poetry.translation = p["translation"].strip()
        if (p.get("appreciation") or "").strip():
            poetry.appreciation = p["appreciation"].strip()
        for raw in p.get("rels", []):
            r = _norm_rel(raw)
            if not r["clause"]:
                continue
            dup = db.query(ConceptPoetryRel).filter_by(
                concept_id=concept.id, poetry_id=poetry.id, clause=r["clause"]).first()
            if dup:
                report["rel_skipped"] += 1
                continue
            r["emotion_main"] = emotion_main_of(r["emotion"])
            # 去重：同一概念+诗文+名句不重复导入
            dup = db.query(ConceptPoetryRel).filter_by(
                concept_id=concept.id, poetry_id=poetry.id, clause=r.get("clause", "")
            ).first()
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
                image_url = a.get("image_url") or fallback
                # 封面图自动匹配作品图片：有真实作品图时不再使用水墨占位图
                thumb_url = a.get("thumb_url") or image_url
                artwork = Artwork(
                    name=a["name"], artist=a.get("artist", "佚名"), dynasty_period=a.get("dynasty_period", ""),
                    dynasty_main=normalize_artwork_dynasty(a.get("dynasty_period", ""), a.get("dynasty", "")),
                    material=a.get("material", ""), size=a.get("size", ""),
                    subject_names=normalize_subjects(a.get("subject_names", "")),
                    image_url=image_url, thumb_url=thumb_url,
                    description=a.get("description", ""),
                    is_featured=str(a.get("is_featured", "")).strip().lower() in ("1", "true", "yes", "是"),
                )
                db.add(artwork)
                db.flush()
                report["artwork_new"] += 1
            if not db.query(ConceptArtworkRel).filter_by(concept_id=concept.id, artwork_id=artwork.id).first():
                db.add(ConceptArtworkRel(concept_id=concept.id, artwork_id=artwork.id,
                                         relation_desc=a.get("relation_desc", ""), weight=int(a.get("weight", 1))))
                db.flush()

    # 意象-意象关联（v3：聚焦共现）
    for rel in data.get("relations", []):
        if isinstance(rel, dict):
            to_name, rtype, desc = rel.get("to", ""), rel.get("relation_type", "") or "共现", rel.get("description", "")
        else:
            to_name, rtype, desc = rel[0], rel[1] if len(rel) > 1 and rel[1] else "共现", rel[2] if len(rel) > 2 else ""
        target = db.query(Concept).filter_by(name=to_name).first()
        if not target:
            report["warnings"].append(f"关联目标意象「{to_name}」不存在，已跳过")
            continue
        if not db.query(ConceptRelation).filter_by(from_concept_id=concept.id, to_concept_id=target.id).first():
            db.add(ConceptRelation(from_concept_id=concept.id, to_concept_id=target.id,
                                   relation_type="共现", description=desc))
            report["relation_new"] += 1

    recompute_stats(db, concept)
    # 新诗的翻译/赏析预生成：提交后台线程执行，不阻塞导入接口（LLM 逐首调用耗时较长）
    if report["poetry_new"] > 0 and with_svg:
        pending_ids = []
        for p in data.get("poetries", []):
            poetry = db.query(Poetry).filter_by(title=p["title"], author=p.get("author", "佚名")).first()
            if poetry and (not poetry.translation or not poetry.appreciation):
                pending_ids.append(poetry.id)
        if pending_ids:
            schedule_pregeneration(pending_ids)
    return report


# ═══════════════ 后台预生成（翻译/赏析） ═══════════════
import threading
from collections import deque

_pregen_queue: deque = deque()
_pregen_lock = threading.Lock()
_pregen_active = False


def schedule_pregeneration(poetry_ids: list):
    """把诗文 id 加入后台预生成队列；worker 未运行时延迟 5 秒启动（等待事务提交）"""
    global _pregen_active
    with _pregen_lock:
        _pregen_queue.extend(poetry_ids)
        if _pregen_active:
            return
        _pregen_active = True
    threading.Timer(5.0, _pregen_worker).start()


def _pregen_worker():
    """后台逐首生成翻译/赏析并回写缓存；队列空则退出"""
    global _pregen_active
    from ..database import SessionLocal
    try:
        from ..api.poetry import pregenerate_for_poem
        while True:
            with _pregen_lock:
                if not _pregen_queue:
                    _pregen_active = False
                    return
                pid = _pregen_queue.popleft()
            db = SessionLocal()
            try:
                poetry = db.get(Poetry, pid)
                if poetry and (not poetry.translation or not poetry.appreciation):
                    pregenerate_for_poem(db, poetry)
                    db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()
    except Exception:
        with _pregen_lock:
            _pregen_active = False


# ═══════════════ 格式解析 ═══════════════
def parse_json(text: str) -> list[dict]:
    """JSON → 意象数据包列表"""
    obj = json.loads(text)
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict) and "concepts" in obj:
        return obj["concepts"]
    return [obj]


# ═══════════════ 专项 CSV 入库（v3 新增） ═══════════════
def _match_concept(db: Session, word: str):
    """按名称或别名匹配意象"""
    c = db.query(Concept).filter_by(name=word).first()
    if c:
        return c
    for c in db.query(Concept).all():
        aliases = [a.strip() for a in (c.aliases or "").split(",") if a.strip()]
        if word in aliases:
            return c
    return None


def import_couplets_csv(db: Session, rows: list[dict]) -> dict:
    """对仗 CSV 入库：word_a 能匹配意象则关联，否则 concept_id 置空保留"""
    report = {"inserted": 0, "skipped": 0, "linked_concepts": 0}
    for r in rows:
        concept = _match_concept(db, r["word_a"]) or _match_concept(db, r["word_b"])
        dup = db.query(Couplet).filter_by(word_a=r["word_a"], word_b=r["word_b"], verse=r["verse"]).first()
        if dup:
            if concept and not dup.concept_id:
                dup.concept_id = concept.id
            report["skipped"] += 1
            continue
        db.add(Couplet(concept_id=concept.id if concept else None,
                       word_a=r["word_a"], word_b=r["word_b"],
                       verse=r["verse"], source=r["source"]))
        report["inserted"] += 1
        if concept:
            report["linked_concepts"] += 1
    return report


def import_cooccurrence_csv(db: Session, rows: list[dict]) -> dict:
    """共现分析 CSV 入库：v2 支持 con_word 桥接（word→桥接词→目标）"""
    report = {"inserted": 0, "updated": 0, "relation_synced": 0, "bridge_edges": 0}
    _br_done = set()
    for r in rows:
        con_word = r.get("con_word", "")

        if con_word:
            # ── 桥接链路：word→桥接词(包含) + 桥接词→目标(共现) ──
            ca = _match_concept(db, r["word_a"])
            if ca:
                # 桥接词严格按名称匹配，不走别名（避免桥接词被误判为原意象）
                br = db.query(Concept).filter_by(name=con_word).first()
                if not br:
                    br = Concept(name=con_word, category_main="自然类", category_sub="桥接词", theme_color="#aaaaaa")
                    db.add(br); db.flush()
                if (ca.id, br.id) not in _br_done:
                    _br_done.add((ca.id, br.id))
                    db.add(ConceptRelation(from_concept_id=ca.id, to_concept_id=br.id,
                                           relation_type="包含", npmi=0, diaphaneity=0.3))
                    report["bridge_edges"] += 1
                cb = _match_concept(db, r["word_b"])
                if not cb:
                    cb = Concept(name=r["word_b"], category_main="自然类", category_sub="桥接词", theme_color="#aaaaaa")
                    db.add(cb); db.flush()
                existing_br = db.query(CooccurrenceStat).filter_by(word_a=con_word, word_b=r["word_b"]).first()
                if not existing_br:
                    db.add(CooccurrenceStat(word_a=con_word, word_b=r["word_b"],
                        cooccurrence_type=r.get("cooccurrence_type", ""),
                        same_sentence=r.get("same_sentence", 0), adjacent_sentence=r.get("adjacent_sentence", 0),
                        same_poem=r.get("same_poem", 0), npmi=r.get("npmi", 0.0),
                        diaphaneity=r.get("diaphaneity", 0.2), verse=r.get("verse", ""),
                        description=r.get("description", ""),
                        poem_title=r.get("poem_title", ""), poet=r.get("poet", ""), dynasty=r.get("dynasty", "")))
                    report["inserted"] += 1
                else:
                    for f in ("verse", "description", "poem_title", "poet", "dynasty"):
                        if r.get(f): setattr(existing_br, f, r.get(f))
                if (br.id, cb.id) not in _br_done:
                    _br_done.add((br.id, cb.id))
                    db.add(ConceptRelation(from_concept_id=br.id, to_concept_id=cb.id, relation_type="共现",
                        cooccurrence_type=r.get("cooccurrence_type", ""),
                        same_sentence=r.get("same_sentence", 0), adjacent_sentence=r.get("adjacent_sentence", 0),
                        same_poem=r.get("same_poem", 0), npmi=r.get("npmi", 0.0),
                        diaphaneity=r.get("diaphaneity", 0.2), verse=r.get("verse", ""),
                        description=r.get("description", ""),
                        poem_title=r.get("poem_title", ""), poet=r.get("poet", ""), dynasty=r.get("dynasty", "")))
                    report["relation_synced"] += 1
            continue

        # ── 无桥接词：直接共现 ──

        key = {"word_a": r["word_a"], "word_b": r["word_b"]}
        existing = db.query(CooccurrenceStat).filter_by(**key).first()
        if existing:
            for f in ("cooccurrence_type", "same_sentence", "adjacent_sentence", "same_poem",
                      "npmi", "diaphaneity", "verse", "description", "poem_title", "poet", "dynasty"):
                if r.get(f) or f in ("npmi", "diaphaneity"):
                    setattr(existing, f, r.get(f))
            report["updated"] += 1
        else:
            db.add(CooccurrenceStat(**key, cooccurrence_type=r.get("cooccurrence_type", ""),
                                    same_sentence=r.get("same_sentence", 0),
                                    adjacent_sentence=r.get("adjacent_sentence", 0),
                                    same_poem=r.get("same_poem", 0),
                                    npmi=r.get("npmi", 0.0), diaphaneity=r.get("diaphaneity", 0.2),
                                    verse=r.get("verse", ""), description=r.get("description", ""),
                                    poem_title=r.get("poem_title", ""), poet=r.get("poet", ""), dynasty=r.get("dynasty", "")))
            report["inserted"] += 1
        # 同步到意象关联表（仅当两端都是库内意象）
        ca, cb = _match_concept(db, r["word_a"]), _match_concept(db, r["word_b"])
        if ca and cb and ca.id != cb.id:
            rel = (db.query(ConceptRelation)
                   .filter(((ConceptRelation.from_concept_id == ca.id) & (ConceptRelation.to_concept_id == cb.id))
                           | ((ConceptRelation.from_concept_id == cb.id) & (ConceptRelation.to_concept_id == ca.id)))
                   .first())
            if rel:
                rel.relation_type = "共现"
                rel.cooccurrence_type = r.get("cooccurrence_type", "")
                rel.same_sentence = r.get("same_sentence", 0)
                rel.adjacent_sentence = r.get("adjacent_sentence", 0)
                rel.same_poem = r.get("same_poem", 0)
                rel.npmi = r.get("npmi", 0.0)
                rel.diaphaneity = r.get("diaphaneity", 0.2)
                if r.get("verse"):
                    rel.verse = r["verse"]
                if r.get("description"):
                    rel.description = r["description"]
            else:
                db.add(ConceptRelation(from_concept_id=ca.id, to_concept_id=cb.id,
                                       relation_type="共现", cooccurrence_type=r.get("cooccurrence_type", ""),
                                       same_sentence=r.get("same_sentence", 0),
                                       adjacent_sentence=r.get("adjacent_sentence", 0),
                                       same_poem=r.get("same_poem", 0),
                                       npmi=r.get("npmi", 0.0), diaphaneity=r.get("diaphaneity", 0.2),
                                       verse=r.get("verse", ""), description=r.get("description", "")))

    return report


def import_emotion_stats_csv(db: Session, rows: list[dict]) -> dict:
    """情感标签占比统计 CSV 入库（按意象词全量覆盖），并回补全库一级情感标签标注"""
    report = {"inserted": 0, "words": 0}
    words = {r["word"] for r in rows}
    if words:
        db.query(EmotionStat).filter(EmotionStat.word.in_(words)).delete(synchronize_session=False)
    for r in rows:
        db.add(EmotionStat(word=r["word"], emotion=r["emotion"], category=r["category"],
                           count=r["count"], ratio=r["ratio"]))
        report["inserted"] += 1
    report["words"] = len(words)
    db.flush()
    # 更新学习映射并回补一级情感标签
    rebuild_learned_map_from_db(db)
    ann = annotate_emotion_main(db)
    report["annotated_rels"] = ann
    return report


def import_dynasty_stats_csv(db: Session, rows: list[dict]) -> dict:
    """朝代出现频次 CSV 入库（按意象词全量覆盖）"""
    report = {"inserted": 0, "words": 0}
    words = {r["word"] for r in rows}
    if words:
        db.query(DynastyOccurrenceStat).filter(DynastyOccurrenceStat.word.in_(words)).delete(synchronize_session=False)
    for r in rows:
        if r["count"] <= 0:
            continue
        db.add(DynastyOccurrenceStat(word=r["word"], dynasty=r["dynasty"], count=r["count"]))
        report["inserted"] += 1
    report["words"] = len(words)
    return report


def import_artworks_csv(db: Session, rows: list[dict]) -> dict:
    """艺术品 CSV 入库：按 名称+作者 去重（已有则补全空缺字段），并建立意象关联"""
    report = {"inserted": 0, "updated": 0, "rel_new": 0, "warnings": []}

    # ── 第一遍：为「新作品且无图片」生成水墨占位 SVG ──
    need_svg = []
    for r in rows:
        existing = db.query(Artwork).filter_by(name=r["name"], artist=r.get("artist", "佚名")).first()
        if not existing and not r.get("image_url"):
            need_svg.append(r)
    svg_files: list[str] = []
    if need_svg:
        import sys
        backend_root = Path(__file__).resolve().parent.parent.parent
        if str(backend_root) not in sys.path:
            sys.path.insert(0, str(backend_root))
        from scripts.svg_art import ensure_artwork_svgs
        svg_dir = backend_root / "app" / "static" / "artworks"
        try:
            svg_files = ensure_artwork_svgs(need_svg, svg_dir)
        except Exception:
            svg_files = []
    svg_iter = iter(svg_files)

    # ── 第二遍：写入/补全 ──
    for r in rows:
        artist = r.get("artist", "佚名")
        period = r.get("dynasty_period") or r.get("dynasty") or ""
        # 去重：优先 name+artist，其次仅 name，自动合并关联关系
        artwork = db.query(Artwork).filter_by(name=r["name"], artist=artist).first()
        if not artwork:
            artwork = db.query(Artwork).filter_by(name=r["name"]).first()
        if artwork:
            report["updated"] += 1
            for src, dst in (("material", "material"), ("size", "size"),
                             ("subject_names", "subject_names"), ("description", "description")):
                if r.get(src) and not getattr(artwork, dst):
                    setattr(artwork, dst, normalize_subjects(r[src]) if dst == "subject_names" else r[src])
            if period and not artwork.dynasty_period:
                artwork.dynasty_period = period
            if r.get("is_featured"): artwork.is_featured = str(r.get("is_featured", "")).strip().lower() in ("1", "true", "yes", "是")
            if r.get("image_url") and (not artwork.image_url or artwork.image_url.endswith(".svg")):
                artwork.image_url = r["image_url"]
                artwork.thumb_url = r["image_url"]
            artwork.dynasty_main = (normalize_artwork_dynasty(artwork.dynasty_period, artwork.dynasty)
                                    or artwork.dynasty_main)
        else:
            image_url = r.get("image_url") or (f"/static/artworks/{next(svg_iter)}" if svg_files else "")
            artwork = Artwork(
                name=r["name"], artist=artist,
                dynasty=r.get("dynasty", ""), dynasty_period=period,
                dynasty_main=normalize_artwork_dynasty(period, r.get("dynasty", "")),
                material=r.get("material", ""), size=r.get("size", ""),
                subject_names=normalize_subjects(r.get("subject_names", "")),
                image_url=image_url, thumb_url=image_url,
                description=r.get("description", ""),
                is_featured=str(r.get("is_featured", "")).strip().lower() in ("1", "true", "yes", "是"),
            )
            db.add(artwork)
            db.flush()
            report["inserted"] += 1

        # ── 意象关联 ──
        if r.get("concepts"):
            for word in re_split(r["concepts"]):
                concept = _match_concept(db, word)
                if not concept:
                    report["warnings"].append(f"《{r['name']}》关联意象「{word}」不在库中，已跳过")
                    continue
                is_feat = str(r.get("is_featured", "")).strip().lower() in ("1", "true", "yes", "是")
                if not db.query(ConceptArtworkRel).filter_by(concept_id=concept.id, artwork_id=artwork.id).first():
                    # 同概念互斥：新设为精选时取消旧的
                    if is_feat:
                        db.query(ConceptArtworkRel).filter(
                            ConceptArtworkRel.concept_id == concept.id,
                            ConceptArtworkRel.is_featured == True,
                        ).update({ConceptArtworkRel.is_featured: False})
                    db.add(ConceptArtworkRel(concept_id=concept.id, artwork_id=artwork.id,
                                             relation_desc=r.get("relation_desc", ""), weight=2,
                                             is_featured=is_feat))
                    db.flush()
                    report["rel_new"] += 1
    return report


def annotate_emotion_main(db: Session) -> int:
    """为所有诗文关联回补一级情感标签（emotion_main），返回更新条数"""
    n = 0
    for r in db.query(ConceptPoetryRel).filter(ConceptPoetryRel.emotion != "").all():
        main = emotion_main_of(r.emotion)
        if main and r.emotion_main != main:
            r.emotion_main = main
            n += 1
    return n


def _unescape_newlines(s: str) -> str:
    """CSV 单元格中的字面 \\n 还原为真换行"""
    return (s or "").replace("\\n", "\n")


def parse_csv(text: str) -> tuple[str, list[dict] | None, list[str]]:
    """按表头自动识别 CSV 类型，返回 (类型, 数据行列表, 错误列表)

    类型：'poetries'（诗文关联）/ 'concepts'（意象本体）/ 'couplets'（对仗）/
          'cooccurrence'（共现分析）/ 'emotion_stats'（情感标签占比）/ 'dynasty_stats'（朝代频次）
    """
    errors: list[str] = []
    reader = csv.DictReader(io.StringIO(text))
    headers = set(reader.fieldnames or [])
    headers_lower = {h.lower().strip() for h in headers}

    def _col(row: dict, *candidates) -> str:
        """按候选列名（忽略大小写与全角括号后缀）取值"""
        for key, val in row.items():
            if key is None:
                continue
            kl = key.lower().strip()
            for c in candidates:
                if kl == c or kl.startswith(c + "（") or kl.startswith(c + "("):
                    return (val or "").strip()
        return ""

    # ── 情感标签占比统计表（imagery_emotion_statistics_aggregated.csv） ──
    if {"word", "emotion_names", "emotion_ratios"} <= headers:
        rows = []
        for i, row in enumerate(reader, start=2):
            word = (row.get("word") or "").strip()
            if not word:
                continue
            names = [x.strip() for x in (row.get("emotion_names") or "").split(";")]
            cats = [x.strip() for x in (row.get("emotion_categories") or "").split(";")]
            counts = [x.strip() for x in (row.get("emotion_counts") or "").split(";")]
            ratios = [x.strip().rstrip("%") for x in (row.get("emotion_ratios") or "").split(";")]
            for idx, name in enumerate(names):
                if not name:
                    continue
                try:
                    count = int(float(counts[idx])) if idx < len(counts) and counts[idx] else 0
                    ratio = float(ratios[idx]) if idx < len(ratios) and ratios[idx] else 0.0
                except ValueError:
                    continue
                rows.append({"word": word, "emotion": name,
                             "category": cats[idx] if idx < len(cats) else "",
                             "count": count, "ratio": ratio})
        return "emotion_stats", rows, errors

    # ── 朝代出现频次统计表：长表格式 word,dynasty,count ──
    if {"word", "dynasty", "count"} <= headers:
        rows = []
        for i, row in enumerate(reader, start=2):
            word = (row.get("word") or "").strip()
            dynasty = (row.get("dynasty") or "").strip()
            if not word or not dynasty:
                continue
            try:
                cnt = int(float((row.get("count") or "0").strip() or 0))
            except ValueError:
                continue
            rows.append({"word": word, "dynasty": dynasty, "count": cnt})
        return "dynasty_stats", rows, errors

    # ── 朝代出现频次统计表（dynasty_occurrence.csv，宽表） ──
    if {"word", "total_occurrence"} <= headers or {"word", "corrected_freq"} <= headers:
        from ..utils.taxonomy import DYNASTY_GROUPS
        period_cols = [h for h in (reader.fieldnames or [])
                       if h not in ("word", "corrected_freq", "total_occurrence")]
        rows = []
        for i, row in enumerate(reader, start=2):
            word = (row.get("word") or "").strip()
            if not word:
                continue
            merged = {g: 0 for g in DYNASTY_GROUPS}
            for col in period_cols:
                group = dynasty_group_of(col)
                if not group:
                    continue
                try:
                    merged[group] += int(float((row.get(col) or "0").strip() or 0))
                except ValueError:
                    continue
            for group, count in merged.items():
                rows.append({"word": word, "dynasty": group, "count": count})
        return "dynasty_stats", rows, errors

    # ── 共现分析表：v2 桥接格式 word/con_word/to ｜标注格式 name/to ｜分析结果 word_a/word_b ──
    is_cooc_bridge = {"word", "to"} <= headers
    is_cooc_annot = {"name", "to"} <= headers and not is_cooc_bridge
    is_cooc_result = ({"word_a", "word_b"} <= headers
                      and any("npmi" in h or h.startswith(("same_poem", "same_sentence",
                                                           "adjacent_sentence", "transparency"))
                              for h in headers_lower))
    if is_cooc_bridge or is_cooc_annot or is_cooc_result:
        rows = []
        for i, row in enumerate(reader, start=2):
            if is_cooc_bridge:
                wa = _col(row, "word")
                bridge = _col(row, "con_word")
                wb = _col(row, "to")
                ctype = _col(row, "cooccurrence_type")
                ss = int(float(_col(row, "same_sentence") or 0) or 0)
                adj = int(float(_col(row, "adjacent_sentence") or 0) or 0)
                sp = int(float(_col(row, "same_poem") or 0) or 0)
                npmi = _col(row, "npmi")
                dia = _col(row, "diaphaneity")
                verse = _col(row, "verse")
                desc = _unescape_newlines(_col(row, "description"))
            elif is_cooc_annot:
                wa, wb = _col(row, "name"), _col(row, "to")
                ctype = _col(row, "cooccurrence_type")
                npmi = _col(row, "npmi")
                dia = _col(row, "diaphaneity")
                verse = _col(row, "verse")
                desc = _unescape_newlines(_col(row, "description"))
                ss = adj = sp = 0
            else:
                wa, wb = _col(row, "word_a"), _col(row, "word_b")
                ctype = _col(row, "cooccurrence_type")
                ss = int(float(_col(row, "same_sentence") or 0) or 0)
                adj = int(float(_col(row, "adjacent_sentence") or 0) or 0)
                sp = int(float(_col(row, "same_poem") or 0) or 0)
                npmi = _col(row, "npmi_sent", "npmi") or _col(row, "npmi_poem")
                dia = _col(row, "transparency", "diaphaneity")
                verse = _col(row, "verse")
                desc = _unescape_newlines(_col(row, "description"))
            if not wa or not wb:
                errors.append(f"第 {i} 行：word_a/name 与 word_b/to 不能为空")
                continue
            if not ctype:
                ctype = dominant_cooccurrence_type(ss, adj, sp) if (ss or adj or sp) else "全诗"
            try:
                npmi_v = max(-1.0, min(1.0, float(npmi))) if npmi else 0.0
            except ValueError:
                npmi_v = 0.0
            try:
                dia_v = max(0.2, float(dia)) if dia else max(0.2, min(1.0, (npmi_v + 1) / 2))
            except ValueError:
                dia_v = 0.2
            rd = {"word_a": wa, "word_b": wb, "cooccurrence_type": ctype,
                  "same_sentence": ss, "adjacent_sentence": adj, "same_poem": sp,
                  "npmi": npmi_v, "diaphaneity": dia_v, "verse": verse, "description": desc,
                  "poem_title": _col(row, "poem_title"), "poet": _col(row, "poet"), "dynasty": _col(row, "dynasty")}
            if is_cooc_bridge and bridge:
                rd["con_word"] = bridge
            rows.append(rd)
        return "cooccurrence", rows, errors

    # ── 对仗表：word_a / word_b / verse / poet / title ──
    if {"word_a", "word_b"} <= headers:
        rows = []
        for i, row in enumerate(reader, start=2):
            wa, wb = _col(row, "word_a"), _col(row, "word_b")
            if not wa or not wb:
                errors.append(f"第 {i} 行：word_a 与 word_b 不能为空")
                continue
            verse = _col(row, "verse")
            poet = _col(row, "poet", "author")
            title = _col(row, "title")
            title = title.strip("《》") if title else ""
            source = f"{poet}《{title}》" if poet and title else (poet or title or _col(row, "source"))
            rows.append({"word_a": wa, "word_b": wb, "verse": verse, "source": source})
        return "couplets", rows, errors

    # ── 艺术品表：name + artist/material/dynasty_period/image_url 等（不含 emotion_tags） ──
    if ("name" in headers and "emotion_tags" not in headers
            and ({"artist", "author", "material", "dynasty", "dynasty_period", "image_url", "size"} & headers)):
        rows = []
        for i, row in enumerate(reader, start=2):
            name = _col(row, "name")
            if not name:
                errors.append(f"第 {i} 行：name（作品名）不能为空")
                continue
            rows.append({
                "name": name,
                "artist": _col(row, "artist", "author") or "佚名",
                "dynasty": _col(row, "dynasty"),
                "dynasty_period": _col(row, "dynasty_period"),
                "material": _col(row, "material"),
                "size": _col(row, "size"),
                "subject_names": _col(row, "subject_names", "subjects", "subject"),
                "image_url": _col(row, "image_url", "image", "img"),
                "description": _unescape_newlines(_col(row, "description")),
                "concepts": _col(row, "concepts", "concept_names", "concept"),
                "relation_desc": _unescape_newlines(_col(row, "relation_desc")),
                "is_featured": _col(row, "is_featured", "is_feature", "featured", "是否精选", "精选"),
            })
        return "artworks", rows, errors

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
                           "translation": _unescape_newlines((row.get("translation") or "").strip()),
                           "appreciation": _unescape_newlines((row.get("appreciation") or "").strip()),
                           "rels": []}
            else:
                # 同诗多行：后行补充翻译/赏析（前行留空时）
                if not pm[key]["translation"] and (row.get("translation") or "").strip():
                    pm[key]["translation"] = _unescape_newlines(row["translation"].strip())
                if not pm[key]["appreciation"] and (row.get("appreciation") or "").strip():
                    pm[key]["appreciation"] = _unescape_newlines(row["appreciation"].strip())
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
    if fmt in ("csv-couplets", "csv-cooccurrence", "csv-emotion_stats", "csv-dynasty_stats", "csv-artworks"):
        return {
            "format": fmt,
            "concept_count": 0,
            "concepts": [],
            "poetry_rows": 0,
            "rel_rows": 0,
            "couplet_rows": len(packs) if fmt == "csv-couplets" else 0,
            "artwork_rows": len(packs) if fmt == "csv-artworks" else 0,
            "row_count": len(packs),
        }
    return {
        "format": fmt,
        "concept_count": len(packs),
        "concepts": [p["concept"]["name"] for p in packs],
        "poetry_rows": sum(len(p.get("poetries", [])) for p in packs),
        "rel_rows": sum(len(pp.get("rels", [])) for p in packs for pp in p.get("poetries", [])),
        "couplet_rows": sum(len(p.get("couplets", [])) for p in packs),
        "artwork_rows": sum(len(p.get("artworks", [])) for p in packs),
    }
