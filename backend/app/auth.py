import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session

from .config import SECRET_KEY, TOKEN_HOURS
from .db import get_db
from . import models


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return f"pbkdf2:{salt}:{pw_hash}"


def verify_password(password: str, stored_hash: str) -> bool:
    if not password or not stored_hash:
        return False
    if stored_hash.startswith("pbkdf2:"):
        parts = stored_hash.split(":")
        if len(parts) == 3:
            _, salt, expected = parts
            computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
            return hmac.compare_digest(computed, expected)
    # Backward compatibility for plain SHA-256 demo hashes
    computed = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(computed, stored_hash)


def make_token(user_id: int, org_id: int | None = None) -> str:
    payload = {
        "sub": str(user_id),
        "org": org_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def _decode(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    try:
        return jwt.decode(authorization[7:], SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")


def current_user(authorization: str | None = Header(None), db: Session = Depends(get_db)) -> models.User:
    data = _decode(authorization)
    user = db.get(models.User, int(data["sub"]))
    if not user:
        raise HTTPException(401, "Unknown user")
    return user


def current_membership(authorization: str | None = Header(None), db: Session = Depends(get_db)) -> models.Membership:
    """The membership for the organization selected after login."""
    data = _decode(authorization)
    if not data.get("org"):
        raise HTTPException(400, "Select an organization first")
    m = (
        db.query(models.Membership)
        .filter_by(user_id=int(data["sub"]), org_id=data["org"])
        .first()
    )
    if not m:
        raise HTTPException(403, "Not a member of this organization")
    return m
