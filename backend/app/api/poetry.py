"""诗文模块接口"""
import json
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Concept, ConceptPoetryRel, Poetry
from ..schemas import ApiResp, PoetrySearchReq
from ..service.tone_service import poem_tones
from ..utils import upstream

router = APIRouter(prefix="/api/poetry", tags=["诗文"])


def _brief(p: Poetry) -> dict:
    return {"id": p.id, "title": p.title, "author": p.author, "dynasty": p.dynasty, "writing_type": p.writing_type}


@router.get("/{poetry_id}")
def poetry_detail(poetry_id: int, db: Session = Depends(get_db)):
    """诗文全文详情（含诗中意象标注，供高亮跳转）"""
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


@router.post("/search")
def poetry_search(req: PoetrySearchReq, db: Session = Depends(get_db)):
    """组合搜索：关键词/朝代/作者/体裁（本地库；上游检索可在此扩展透传）"""
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


@router.get("/{poetry_id}/similar")
def poetry_similar(poetry_id: int, limit: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)):
    """相似句推荐：优先透传上游接口；不可用时基于本地句库相似度计算"""
    p = db.get(Poetry, poetry_id)
    if not p:
        raise HTTPException(404, "诗文不存在")
    clauses = json.loads(p.clauses or "[]")
    key = clauses[0] if clauses else p.title

    if p.source_writing_id:
        up = upstream.similar_clauses(p.source_writing_id)
        if up:
            return ApiResp(data={"source": "upstream", "items": up})

    # 本地相似度：比较各诗句的字符序列
    candidates = []
    all_poems = db.query(Poetry).filter(Poetry.id != p.id).all()
    for other in all_poems:
        other_clauses = json.loads(other.clauses or "[]")
        best, best_clause = 0.0, ""
        for c1 in clauses:
            for c2 in other_clauses:
                s = SequenceMatcher(None, c1, c2).ratio()
                if s > best:
                    best, best_clause = s, c2
        if best > 0.28:
            candidates.append({"score": round(best, 3), "clause": best_clause, "poetry": _brief(other)})
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return ApiResp(data={"source": "local", "key": key, "items": candidates[:limit]})


@router.get("/{poetry_id}/tones")
def poetry_tones(poetry_id: int, db: Session = Depends(get_db)):
    """平仄标注：优先上游；否则本地拼音近似推定（含入声字修正）"""
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


@router.get("/{poetry_id}/book-links")
def poetry_book_links(poetry_id: int, db: Session = Depends(get_db)):
    """古籍出处（透传上游古籍库；本地库无出处数据时返回提示）"""
    p = db.get(Poetry, poetry_id)
    if not p:
        raise HTTPException(404, "诗文不存在")
    if p.source_writing_id:
        up = upstream.writing_book_links(p.source_writing_id)
        if up:
            return ApiResp(data={"source": "upstream", "items": up})
    return ApiResp(data={"source": "local", "items": [],
                         "note": "本地精选库未收录古籍出处信息；配置上游接口后可自动透传。"})


@router.get("/{poetry_id}/labelize")
def poetry_labelize(poetry_id: int, db: Session = Depends(get_db)):
    """自动笺注：优先上游；本地兜底返回诗中意象标注"""
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
                          "note": f"「{c.name}」意象：{c.poetic_meaning[:60]}……"})
    return ApiResp(data={"source": "local", "items": items})
