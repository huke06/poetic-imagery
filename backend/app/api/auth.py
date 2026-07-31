"""账号系统：注册 / 登录 / 找回密码 / 个人信息"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import auth as auth_utils
from ..database import get_db
from ..models import User
from ..schemas import ApiResp

router = APIRouter(prefix="/api/auth", tags=["账号"])

# 简易数学验证码缓存
import random, time
_captcha_store: dict[str, tuple[int, float]] = {}  # id → (answer, expires_at)


@router.get("/captcha")
def get_captcha():
    """返回数学验证码题目（图片渲染在前端 Canvas）"""
    cid = __import__('secrets').token_hex(8)
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    op = random.choice(["+", "×"])
    answer = a + b if op == "+" else a * b
    _captcha_store[cid] = (answer, time.time() + 300)  # 5 分钟有效
    return ApiResp(data={"id": cid, "question": f"{a} {op} {b} = ?"})


def _check_captcha(captcha_id: str, captcha_answer: str):
    if not captcha_id or captcha_id not in _captcha_store:
        raise HTTPException(400, "验证码已过期，请刷新")
    ans, expires = _captcha_store[captcha_id]
    if time.time() > expires:
        _captcha_store.pop(captcha_id, None)
        raise HTTPException(400, "验证码已过期")
    try:
        if int(captcha_answer) != ans:
            raise HTTPException(400, "验证码错误")
    except ValueError:
        raise HTTPException(400, "验证码答案须为数字")
    _captcha_store.pop(captcha_id, None)


class RegisterReq(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    email: str = Field(default="")
    password: str = Field(min_length=6, max_length=64)
    captcha_id: str = ""
    captcha_answer: str = ""


class LoginReq(BaseModel):
    username: str
    password: str
    captcha_id: str = ""
    captcha_answer: str = ""


class ResetReq(BaseModel):
    email: str


@router.post("/register")
def register(req: RegisterReq, db: Session = Depends(get_db)):
    _check_captcha(req.captcha_id, req.captcha_answer)
    if db.query(User).filter_by(username=req.username).first():
        raise HTTPException(400, "用户名已被使用")
    user = User(
        username=req.username,
        email=req.email,
        password_hash=auth_utils.hash_pw(req.password),
        role="user",
    )
    db.add(user)
    db.commit()
    token = auth_utils.create_token(user.id)
    return ApiResp(data={"token": token, "user": {"id": user.id, "username": user.username, "role": user.role}})


@router.post("/login")
def login(req: LoginReq, db: Session = Depends(get_db)):
    _check_captcha(req.captcha_id, req.captcha_answer)
    user = db.query(User).filter_by(username=req.username).first()
    if not user or not auth_utils.verify_pw(req.password, user.password_hash):
        raise HTTPException(400, "用户名或密码错误")
    if not user.is_active:
        raise HTTPException(403, "账号已被禁用")
    token = auth_utils.create_token(user.id)
    return ApiResp(data={"token": token, "user": {"id": user.id, "username": user.username, "role": user.role}})


@router.post("/reset-password")
def reset_password(req: ResetReq, db: Session = Depends(get_db)):
    if not req.email:
        raise HTTPException(400, "请输入注册邮箱")
    user = db.query(User).filter_by(email=req.email).first()
    if not user:
        raise HTTPException(404, "未找到该邮箱关联的账号")
    new_pw = auth_utils.reset_token(req.email)
    user.password_hash = auth_utils.hash_pw(new_pw)
    db.commit()
    return ApiResp(data={"new_password": new_pw, "note": "请登录后立即修改密码。此为本地开发环境，重置密码已直接返回；生产环境应发送邮件。"})


@router.get("/me")
def me(user: User = Depends(auth_utils.get_current_user)):
    return ApiResp(data={"id": user.id, "username": user.username, "email": user.email,
                         "role": user.role, "avatar": user.avatar, "create_time": str(user.create_time)})
