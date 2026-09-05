from datetime import datetime, timedelta, timezone
import hashlib
import hmac

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def password_version(hashed_password: str) -> str:
    return hmac.new(settings.jwt_secret.encode(), hashed_password.encode(), hashlib.sha256).hexdigest()


def create_access_token(subject: str, hashed_password: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire, "pwdv": password_version(hashed_password)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm],
                             options={"require_exp": True, "require_sub": True})
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject.isascii() or not subject.isdigit() or len(subject) > 18 or int(subject) < 1:
            return None
        version = payload.get("pwdv")
        if not isinstance(version, str) or len(version) != 64 or any(char not in "0123456789abcdef" for char in version):
            return None
        return payload
    except (JWTError, ValueError, TypeError):
        return None
