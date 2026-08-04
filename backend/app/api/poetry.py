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


# ═══════════════ 诗词翻译（DB 缓存 + LLM 生成） ═══════════════
@router.get("/{poetry_id}/translate")
def poetry_translate(poetry_id: int, db: Session = Depends(get_db)):
    """现代汉语翻译：DB 缓存优先 → LLM 生成 → 回写缓存"""
    p = db.get(Poetry, poetry_id)
    if not p:
        raise HTTPException(404, "诗文不存在")
    if p.translation:
        return ApiResp(data={"source": "cache", "text": p.translation})

    if llm.llm_available():
        prompt = (
            f"请将下面这首古典诗词逐句翻译为现代汉语，保留原诗的意境和情感基调，语言典雅流畅。"
            f"每行格式：原文 → 译文\n\n《{p.title}》\n{p.content}"
        )
        result = llm.chat([
            {"role": "system", "content": "你是古典诗词翻译专家，逐句翻译为现代汉语，保留意境。仅输出纯文本，不要使用任何 Markdown 符号（如 **、#、- 等）。"},
            {"role": "user", "content": prompt},
        ], temperature=0.3)
        if result:
            p.translation = result
            db.commit()
            return ApiResp(data={"source": "llm", "text": result})

    return ApiResp(data={"source": "local", "text": "",
                         "note": "诗词翻译需配置大模型。在管理后台「系统配置」中填入 API Key 后即可使用。"})


# ═══════════════ 诗词赏析（DB 缓存 + LLM 生成） ═══════════════
@router.get("/{poetry_id}/appreciation")
def poetry_appreciation(poetry_id: int, db: Session = Depends(get_db)):
    """文学赏析：DB 缓存优先 → LLM 生成 → 回写缓存"""
    p = db.get(Poetry, poetry_id)
    if not p:
        raise HTTPException(404, "诗文不存在")
    if p.appreciation:
        return ApiResp(data={"source": "cache", "text": p.appreciation})

    if llm.llm_available():
        prompt = (
            f"请从意象运用、情感表达、艺术手法三个角度，对下面这首诗词做 200-300 字的文学赏析。\n\n"
            f"《{p.title}》·{p.dynasty}·{p.author}\n{p.content}"
        )
        result = llm.chat([
            {"role": "system", "content": "你是古典诗词鉴赏专家，赏析聚焦意象、情感、手法，简要精当。仅输出纯文本，不要使用任何 Markdown 符号（如 **、#、- 等）。"},
            {"role": "user", "content": prompt},
        ], temperature=0.5)
        if result:
            p.appreciation = result
            db.commit()
            return ApiResp(data={"source": "llm", "text": result})

    return ApiResp(data={"source": "local", "text": "",
                         "note": "诗词赏析需配置大模型。在管理后台「系统配置」中填入 API Key 后即可使用。"})


# ═══════════════ 批量预生成（导入后调用，后台触发） ═══════════════
def pregenerate_for_poem(db: Session, p: Poetry):
    """为单首诗文异步预生成翻译与赏析（已有则跳过）；导入/重建后可调用"""
    if not llm.llm_available():
        return
    if not p.translation:
        prompt_tr = (
            f"请将下面这首古典诗词逐句翻译为现代汉语，保留原诗的意境和情感基调，语言典雅流畅。"
            f"每行格式：原文 → 译文\n\n《{p.title}》\n{p.content}"
        )
        try:
            tr = llm.chat([
                {"role": "system", "content": "你是古典诗词翻译专家，逐句翻译为现代汉语。仅输出纯文本，不要使用任何 Markdown 符号（如 **、#、- 等）。"},
                {"role": "user", "content": prompt_tr},
            ], temperature=0.3)
            if tr:
                p.translation = tr
        except Exception:
            pass
    if not p.appreciation:
        prompt_ap = (
            f"请从意象运用、情感表达、艺术手法三个角度，对下面这首诗词做 200-300 字的文学赏析。\n\n"
            f"《{p.title}》·{p.dynasty}·{p.author}\n{p.content}"
        )
        try:
            ap = llm.chat([
                {"role": "system", "content": "你是古典诗词鉴赏专家，赏析聚焦意象、情感、手法，简要精当。仅输出纯文本，不要使用任何 Markdown 符号（如 **、#、- 等）。"},
                {"role": "user", "content": prompt_ap},
            ], temperature=0.5)
            if ap:
                p.appreciation = ap
        except Exception:
            pass


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
        if not c:
            continue
        # 缓存命中直接返回
        if r.annotation:
            items.append({"clause": r.clause, "concept": c.name, "emotion": r.emotion, "note": r.annotation})
            continue
        # 生成笺注
        note = _generate_annotation(p, r, c)
        if note:
            r.annotation = note
            db.commit()
        items.append({"clause": r.clause, "concept": c.name, "emotion": r.emotion, "note": note})
    return ApiResp(data={"source": "local", "items": items})


def _generate_annotation(p, r, c) -> str:
    """生成逐句笺注：LLM 深度解析 → 写入缓存；无 LLM 时用模板"""
    if llm.llm_available():
        try:
            prompt = (
                f"请对下面这句诗做 80-120 字的文学笺注，围绕「{c.name}」意象展开：\n"
                f"① 此意象在本句中的具体作用与画面感\n"
                f"② 它与全诗主题的关联\n"
                f"③ 所承载的情感（{r.emotion}）如何通过此意象传达\n\n"
                f"诗句：「{r.clause}」\n全诗：《{p.title}》（{p.dynasty}·{p.author}）\n"
                f"情感标签：{r.emotion or '未标注'}"
            )
            result = llm.chat([
                {"role": "system", "content": "你是古典诗词笺注专家，做 80-120 字深度解析，聚焦意象在句中的具体作用。仅输出纯文本，不要使用任何 Markdown 符号。"},
                {"role": "user", "content": prompt},
            ], temperature=0.4, timeout=15)
            if result and len(result.strip()) >= 20:
                return result.strip()
        except Exception:
            pass
    # 本地模板兜底
    meanings = {
        "怀人": "以月为媒，寄托对远方故人的深切思念",
        "思乡": "望月兴怀，触发了游子对故乡的无尽眷恋",
        "孤寂": "月悬夜空，映照出诗人独处时的清冷与落寞",
        "时空永恒": "借月之亘古长存，反衬人世须臾、历史沧桑",
        "离愁": "暮色中寄寓离别的怅惘与不舍",
        "怀古": "以残照旧迹牵引对往昔繁华的追念与兴废之叹",
        "落寞": "日暮途远，写尽个体在苍茫天地间的萧索与失意",
        "时光流逝": "夕阳西沉如年华逝水，暗含对光阴不再的深沉感喟",
        "惜春": "以柳色春景，抒发对春光易逝的婉惜与留恋",
        "苍凉": "景物萧瑟，意境旷远而悲壮",
        "豪迈": "以开阔之境写慷慨之志，气吞山河",
        "厌战": "以征伐之苦与牺牲之痛，表达对和平的渴望",
    }
    base = meanings.get(r.emotion, f"以「{c.name}」为象，承载了{r.emotion or '诗人'}的情感寄托")
    return f"此句写「{r.clause}」。{base}。{c.poetic_meaning[:60]}……"


# 后台批量预生成所有笺注
@router.post("/{poetry_id}/labelize/generate")
def generate_labelize(poetry_id: int, db: Session = Depends(get_db)):
    """为这首诗的所有关联句批量生成并缓存笺注（后台/导入后调用）"""
    p = db.get(Poetry, poetry_id)
    if not p:
        raise HTTPException(404, "诗文不存在")
    rels = db.query(ConceptPoetryRel).filter_by(poetry_id=p.id, annotation="").all()
    generated = 0
    for r in rels:
        c = db.get(Concept, r.concept_id)
        if not c:
            continue
        note = _generate_annotation(p, r, c)
        if note:
            r.annotation = note
            generated += 1
    db.commit()
    return ApiResp(data={"generated": generated, "total": len(rels)})
