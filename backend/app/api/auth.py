"""账号系统：注册 / 登录 / 修改密码 / 个人信息"""
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import auth as auth_utils
from ..database import get_db
from ..models import User
from ..schemas import ApiResp

router = APIRouter(prefix="/api/auth", tags=["账号"])

# 登录防爆破：username+ip → (连续失败次数, 锁定截止时间戳)
_fail_store: dict[tuple[str, str], tuple[int, float]] = {}
MAX_FAILS = 5
LOCK_SECONDS = 300


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _check_lockout(username: str, ip: str):
    key = (username, ip)
    if key in _fail_store:
        fails, locked_until = _fail_store[key]
        if time.time() < locked_until:
            remain = int(locked_until - time.time())
            raise HTTPException(429, f"尝试次数过多，请 {remain} 秒后再试")
        _fail_store.pop(key, None)


def _record_fail(username: str, ip: str):
    key = (username, ip)
    fails = (_fail_store.get(key, (0, 0))[0] if key in _fail_store else 0) + 1
    _fail_store[key] = (fails, time.time() + LOCK_SECONDS if fails >= MAX_FAILS else 0)


def _clear_fail(username: str, ip: str):
    _fail_store.pop((username, ip), None)


class RegisterReq(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    email: str = Field(default="", max_length=128)
    password: str = Field(min_length=6, max_length=64)


class LoginReq(BaseModel):
    username: str
    password: str


class ChangePasswordReq(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=64)


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
def login(req: LoginReq, request: Request, db: Session = Depends(get_db)):
    ip = _client_ip(request)
    _check_lockout(req.username, ip)
    user = db.query(User).filter_by(username=req.username).first()
    if not user or not auth_utils.verify_pw(req.password, user.password_hash):
        _record_fail(req.username, ip)
        raise HTTPException(400, "用户名或密码错误")
    if not user.is_active:
        raise HTTPException(403, "账号已被禁用")
    _clear_fail(req.username, ip)
    token = auth_utils.create_token(user.id)
    return ApiResp(data={"token": token, "user": {"id": user.id, "username": user.username, "role": user.role}})


@router.post("/change-password")
def change_password(req: ChangePasswordReq, user: User = Depends(auth_utils.get_current_user),
                    db: Session = Depends(get_db)):
    if not auth_utils.verify_pw(req.old_password, user.password_hash):
        raise HTTPException(400, "原密码错误")
    user.password_hash = auth_utils.hash_pw(req.new_password)
    db.commit()
    return ApiResp(msg="密码已修改")


@router.get("/me")
def me(user: User = Depends(auth_utils.get_current_user)):
    return ApiResp(data={"id": user.id, "username": user.username, "email": user.email,
                         "role": user.role, "avatar": user.avatar, "create_time": str(user.create_time)})
