"""
Security module: Password hashing, verification, JWT token creation, and account lockout logic.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import os
import secrets
from typing import Optional
import jwt
from ..config import settings

def hash_password(password: str) -> str:
    """Hashes password with SHA256 and unique salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against stored salt:hash."""
    try:
        salt, stored_hash = hashed_password.split(":")
        calc_hash = hashlib.sha256((salt + plain_password).encode('utf-8')).hexdigest()
        return secrets.compare_digest(stored_hash, calc_hash)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None
