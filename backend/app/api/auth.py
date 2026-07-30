"""账号系统：注册 / 登录 / 找回密码 / 个人信息"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import auth as auth_utils
from ..database import get_db
from ..models import User
from ..schemas import ApiResp

router = APIRouter(prefix="/api/auth", tags=["账号"])


class RegisterReq(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    email: str = Field(default="")
    password: str = Field(min_length=6, max_length=64)


class LoginReq(BaseModel):
    username: str
    password: str


class ResetReq(BaseModel):
    email: str


@router.post("/register")
def register(req: RegisterReq, db: Session = Depends(get_db)):
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
