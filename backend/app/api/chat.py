"""聊天记录持久化：会话管理 + 消息存取 + 上下文构建"""
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import auth as auth_utils
from ..database import get_db
from ..models import ChatConversation, ChatMessage, User
from ..schemas import ApiResp
from ..service import agent_service
from ..utils import llm

router = APIRouter(prefix="/api/chat", tags=["聊天"])


@router.get("/conversations")
def list_conversations(
    user: User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    convs = (
        db.query(ChatConversation)
        .filter_by(user_id=user.id)
        .order_by(ChatConversation.update_time.desc())
        .all()
    )
    return ApiResp(data=[{"id": c.id, "title": c.title, "source": c.source,
                          "create_time": str(c.create_time), "update_time": str(c.update_time)} for c in convs])


@router.post("/conversations")
def create_conversation(
    source: str = Query("ask"),
    user: User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    c = ChatConversation(user_id=user.id, source=source, title="新对话")
    db.add(c)
    db.commit()
    return ApiResp(data={"id": c.id})


@router.delete("/conversations/{conv_id}")
def delete_conversation(
    conv_id: int,
    user: User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    c = db.get(ChatConversation, conv_id)
    if not c or c.user_id != user.id:
        raise HTTPException(404, "会话不存在")
    db.delete(c)
    db.commit()
    return ApiResp()


@router.get("/conversations/{conv_id}/messages")
def get_messages(
    conv_id: int,
    user: User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    c = db.get(ChatConversation, conv_id)
    if not c or c.user_id != user.id:
        raise HTTPException(404, "会话不存在")
    msgs = (
        db.query(ChatMessage)
        .filter_by(conversation_id=conv_id)
        .order_by(ChatMessage.id)
        .all()
    )
    return ApiResp(data=[{
        "id": m.id, "role": m.role, "text": m.text, "source": m.source,
        "references": json.loads(m.references_json or "{}"),
        "create_time": str(m.create_time),
    } for m in msgs])


class AskInConv(BaseModel):
    conversation_id: int = 0
    question: str = Field(min_length=1)
    mode: str = "ask"         # ask / compose
    style: str = ""           # compose 体裁
    theme: str = ""           # compose 情感基调
    concepts: list[str] = Field(default_factory=list)  # compose 意象


@router.post("/send")
def send_message(
    req: AskInConv,
    user: User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    # 1. 解析或新建会话
    conv = None
    if req.conversation_id:
        conv = db.get(ChatConversation, req.conversation_id)
        if not conv or conv.user_id != user.id:
            raise HTTPException(404, "会话不存在")
    if not conv:
        title = req.question[:24] + ("…" if len(req.question) > 24 else "")
        conv = ChatConversation(user_id=user.id, source=req.mode, title=title)
        db.add(conv)
        db.flush()

    # 2. 构建上下文（最近 8 条消息，含用户和 AI，按时间排序）
    prev = (
        db.query(ChatMessage)
        .filter_by(conversation_id=conv.id)
        .order_by(ChatMessage.id.desc())
        .limit(8).all()
    )
    context_msgs = [{"role": m.role, "content": m.text[:300]} for m in reversed(prev)]

    # 3. 保存用户消息
    um = ChatMessage(conversation_id=conv.id, role="user", text=req.question, source="")
    db.add(um)
    db.flush()

    # 4. 生成回答
    if req.mode == "compose":
        data = agent_service.compose(db, req.concepts or ["月"], req.style or "七言绝句", req.theme)
        answer_text = f"为您创作一首{data['style']}：\n\n**《{data['title']}》**\n\n{data['poem']}"
        if data.get("tones"):
            tones_str = "\n".join(f"· {t['clause']} {t['tone_string']}" for t in data["tones"])
            answer_text += f"\n\n平仄标注：\n{tones_str}"
        if data.get("note"):
            answer_text += f"\n\n{data['note']}"
        refs = {}
    else:
        # ask mode — 传入完整对话上下文（含角色）
        data = agent_service.ask(db, req.question, context_msgs)
        answer_text = data["answer"]
        refs = data.get("references", {})

    # 5. 保存 AI 回复
    am = ChatMessage(conversation_id=conv.id, role="ai", text=answer_text,
                     source=data.get("source", "local"),
                     references_json=json.dumps(refs, ensure_ascii=False))
    db.add(am)
    # 自动用首条用户问题作会话标题
    if conv.title == "新对话" and req.mode == "ask":
        conv.title = req.question[:24] + ("…" if len(req.question) > 24 else "")
    db.commit()

    return ApiResp(data={
        "conversation_id": conv.id, "title": conv.title,
        "message": {"id": am.id, "role": "ai", "text": am.text, "source": am.source,
                     "references": refs, "create_time": str(am.create_time)},
    })
