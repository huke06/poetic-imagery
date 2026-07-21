"""智能问答模块接口"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import ApiResp, AskReq, ComposeReq
from ..service import agent_service

router = APIRouter(prefix="/api/agent", tags=["智能助手"])


@router.post("/ask")
def agent_ask(req: AskReq, db: Session = Depends(get_db)):
    """智能问答：本地知识库检索 + 模板/大模型生成，回答全部锚定库中数据"""
    return ApiResp(data=agent_service.ask(db, req.question))


@router.post("/compose")
def agent_compose(req: ComposeReq, db: Session = Depends(get_db)):
    """意象创诗：输入意象+体裁，生成古诗并附平仄标注"""
    return ApiResp(data=agent_service.compose(db, req.concepts, req.style, req.theme))
