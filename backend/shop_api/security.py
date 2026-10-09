from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re

import jwt
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import JWT_SECRET, PAYMENT_ENCRYPTION_KEY
from .database import get_session
from .models import User

security = HTTPBearer(auto_error=False)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> int:
    if not credentials:
        raise HTTPException(401, "请先登录")
    try:
        return int(jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as error:
        raise HTTPException(401, "请先登录") from error


def active_user(user_id: int = Depends(current_user), session: Session = Depends(get_session)) -> int:
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(401, "请先登录")
    if user.status == "disabled":
        raise HTTPException(403, "该用户已停用")
    return user_id


def current_admin(user_id: int = Depends(active_user), session: Session = Depends(get_session)) -> int:
    user = session.get(User, user_id)
    if not user or user.role != "admin":
        raise HTTPException(403, "仅管理员可访问")
    return user_id


def issue_token(user_id: int) -> str:
    return jwt.encode({"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(hours=12)}, JWT_SECRET, algorithm="HS256")


def normalized_card_number(card_number: str) -> str:
    number = re.sub(r"[ -]", "", card_number)
    if not number.isdigit() or not 12 <= len(number) <= 19:
        raise HTTPException(400, "请输入 12 至 19 位银行卡号")
    checksum = sum((value * 2 - 9 if value > 4 else value * 2) if index % 2 else value for index, value in enumerate(reversed([int(value) for value in number])))
    if checksum % 10:
        raise HTTPException(400, "银行卡号校验未通过")
    return number


def card_fingerprint(card_number: str) -> str:
    return hmac.new(PAYMENT_ENCRYPTION_KEY.encode(), card_number.encode(), hashlib.sha256).hexdigest()
