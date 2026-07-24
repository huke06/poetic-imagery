"""诗文模块接口"""
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Concept, ConceptPoetryRel, Poetry
from ..schemas import ApiResp, PoetrySearchReq
from ..service.tone_service import poem_tones
from ..utils import llm, upstream

router = APIRouter(prefix="/api/poetry", tags=["诗文"])


def _brief(p: Poetry) -> dict:
    return {"id": p.id, "title": p.title, "author": p.author, "dynasty": p.dynasty, "writing_type": p.writing_type}


# ═══════════════ 正文 ═══════════════
@router.get("/{poetry_id}")
def poetry_detail(poetry_id: int, db: Session = Depends(get_db)):
    p = db.get(Poetry, poetry_id)
    if not p:
        raise HTTPException(404, "诗文不存在")
    rels = db.query(ConceptPoetryRel).filter_by(poetry_id=p.id).all()
    concept_map: dict[int, dict] = {}
    for r in rels:
        c = db.get(Concept, r.concept_id)
        if not c:
            continue
        entry = concept_map.setdefault(c.id, {"id": c.id, "name": c.name, "theme_color": c.theme_color, "clauses": []})
        entry["clauses"].append(r.clause)
    return ApiResp(data={
        **_brief(p), "content": p.content,
        "clauses": json.loads(p.clauses or "[]"),
        "concepts": list(concept_map.values()),
        "create_time": str(p.create_time),
    })


# ═══════════════ 搜索 ═══════════════
@router.post("/search")
def poetry_search(req: PoetrySearchReq, db: Session = Depends(get_db)):
    q = db.query(Poetry)
    if req.key:
        like = f"%{req.key}%"
        q = q.filter((Poetry.title.like(like)) | (Poetry.author.like(like)) | (Poetry.content.like(like)))
    if req.dynasty:
        q = q.filter(Poetry.dynasty == req.dynasty)
    if req.author:
        q = q.filter(Poetry.author.like(f"%{req.author}%"))
    if req.writing_type:
        q = q.filter(Poetry.writing_type == req.writing_type)
    total = q.count()
    rows = q.order_by(Poetry.id).offset((req.page - 1) * req.page_size).limit(req.page_size).all()
    return ApiResp(data={"total": total, "page": req.page, "page_size": req.page_size,
                         "items": [_brief(p) for p in rows]})


# ═══════════════ 相似作品（2-gram Jaccard 相似度） ═══════════════
_BIGRAM_CACHE: dict[int, set[str]] = {}


def _bigrams(text: str) -> set[str]:
    """中文 2-gram 分词，用于 Jaccard 相似度"""
    chars = [ch for ch in text if "一" <= ch <= "鿿"]
    return {chars[i] + chars[i + 1] for i in range(len(chars) - 1)}


@router.get("/{poetry_id}/similar")
def poetry_similar(poetry_id: int, limit: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)):
    """相似句推荐：上游优先；本地 2-gram Jaccard 相似度"""
    p = db.get(Poetry, poetry_id)
    if not p:
        raise HTTPException(404, "诗文不存在")

    if p.source_writing_id:
        up = upstream.similar_clauses(p.source_writing_id)
        if up:
            return ApiResp(data={"source": "upstream", "items": up})

    key_clauses = json.loads(p.clauses or "[]")
    key = key_clauses[0] if key_clauses else p.title
    my_bigrams = _bigrams(p.content)
    if not my_bigrams:
        return ApiResp(data={"source": "local", "key": key, "items": []})

    candidates = []
    all_poems = db.query(Poetry).filter(Poetry.id != p.id).all()
    for other in all_poems:
        ob = _bigrams(other.content)
        if not ob:
            continue
        intersection = len(my_bigrams & ob)
        union = len(my_bigrams | ob)
        score = intersection / union if union > 0 else 0.0
        if score > 0.06:  # 有效阈值（共享 ~6% 以上的 2-gram）
            candidates.append({"score": round(score, 3), "poetry": _brief(other)})
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return ApiResp(data={"source": "local", "key": key, "items": candidates[:limit]})


# ═══════════════ 平仄标注 ═══════════════
@router.get("/{poetry_id}/tones")
def poetry_tones(poetry_id: int, db: Session = Depends(get_db)):
    p = db.get(Poetry, poetry_id)
    if not p:
        raise HTTPException(404, "诗文不存在")
    if p.source_writing_id:
        up = upstream.writing_tones(p.source_writing_id)
        if up:
            return ApiResp(data={"source": "upstream", "items": up})
    clauses = json.loads(p.clauses or "[]")
    return ApiResp(data={"source": "local", "note": "现代读音近似推定，仅供参考",
                         "items": poem_tones(clauses)})


# ═══════════════ 诗词翻译（替代原「古籍出处」） ═══════════════
@router.get("/{poetry_id}/translate")
def poetry_translate(poetry_id: int, db: Session = Depends(get_db)):
    """现代汉语翻译：LLM 优先，本地兜底说明"""
    p = db.get(Poetry, poetry_id)
    if not p:
        raise HTTPException(404, "诗文不存在")

    if llm.llm_available():
        prompt = (
            f"请将下面这首古典诗词逐句翻译为现代汉语，保留原诗的意境和情感基调，语言典雅流畅。"
            f"每行格式：原文 → 译文\n\n《{p.title}》\n{p.content}"
        )
        result = llm.chat([
            {"role": "system", "content": "你是古典诗词翻译专家，逐句翻译为现代汉语，保留意境。"},
            {"role": "user", "content": prompt},
        ], temperature=0.3)
        if result:
            return ApiResp(data={"source": "llm", "text": result})

    return ApiResp(data={"source": "local", "text": "",
                         "note": "诗词翻译需配置大模型。在管理后台「系统配置」中填入 API Key 后即可使用。"})


# ═══════════════ 自动笺注 ═══════════════
@router.get("/{poetry_id}/labelize")
def poetry_labelize(poetry_id: int, db: Session = Depends(get_db)):
    p = db.get(Poetry, poetry_id)
    if not p:
        raise HTTPException(404, "诗文不存在")
    if p.source_writing_id:
        up = upstream.writing_labelize(p.source_writing_id)
        if up:
            return ApiResp(data={"source": "upstream", "items": up})
    rels = db.query(ConceptPoetryRel).filter_by(poetry_id=p.id).all()
    items = []
    for r in rels:
        c = db.get(Concept, r.concept_id)
        if c:
            items.append({"clause": r.clause, "concept": c.name, "emotion": r.emotion,
                          "note": f"「{c.name}」意象：{c.poetic_meaning}"})
    return ApiResp(data={"source": "local", "items": items})
