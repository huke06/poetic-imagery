"""JWT 认证工具：令牌签发/校验 + hashlib 加盐密码哈希"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .config import settings as s
from .database import get_db
from .models import User

SECRET_KEY = s.ADMIN_TOKEN + "jwt-secret-2026-poetic-imagery"
ALGORITHM = "HS256"
TOKEN_EXPIRE = timedelta(days=30)

bearer = HTTPBearer(auto_error=False)


def hash_pw(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"sha:{salt}:{h}"


def verify_pw(plain: str, hashed: str) -> bool:
    try:
        parts = hashed.split(":", 2)
        if len(parts) != 3 or parts[0] != "sha":
            return False
        salt, expected = parts[1], parts[2]
        return hashlib.sha256((salt + plain).encode()).hexdigest() == expected
    except (ValueError, AttributeError):
        return False


def create_token(user_id: int) -> str:
    payload = {"sub": str(user_id), "exp": datetime.now(timezone.utc) + TOKEN_EXPIRE}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> int | None:
    try:
        return int(jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"])
    except (JWTError, ValueError):
        return None


def get_optional_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User | None:
    if not cred:
        return None
    uid = decode_token(cred.credentials)
    if uid is None:
        return None
    return db.get(User, uid)


def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not cred:
        raise HTTPException(401, "请先登录")
    uid = decode_token(cred.credentials)
    if uid is None:
        raise HTTPException(401, "登录已过期，请重新登录")
    user = db.get(User, uid)
    if not user:
        raise HTTPException(401, "用户不存在")
    return user


def get_admin_user(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(403, "需要管理员权限")
    return user


def reset_token(email: str) -> str:
    h = hashlib.md5((email + SECRET_KEY).encode()).hexdigest()[:8]
    return h.upper()
