# JWT auth functions here
import datetime as dt, os, pathlib
from jose import jwt
from fastapi import HTTPException, status
from app.config import settings

ALG = settings.jwt_alg
PRIVATE = None
PUBLIC = None

def _load_keys():
    global PRIVATE, PUBLIC
    if PRIVATE and PUBLIC:
        return
    priv_path = pathlib.Path(settings.jwt_private_key_path)
    pub_path = pathlib.Path(settings.jwt_public_key_path)
    PRIVATE = priv_path.read_text() if priv_path.exists() else None
    PUBLIC  = pub_path.read_text() if pub_path.exists() else None

def create_token(sub: str, scopes: list[str]):
    _load_keys()
    if not PRIVATE:
        raise RuntimeError("JWT private key not found")
    now = dt.datetime.utcnow()
    payload = {"sub": sub, "scope":" ".join(scopes), "iat": now, "exp": now + dt.timedelta(minutes=settings.access_token_expires_min)}
    return jwt.encode(payload, PRIVATE, algorithm=ALG)

def verify_token(token: str) -> dict:
    _load_keys()
    if not PUBLIC:
        raise RuntimeError("JWT public key not found")
    try:
        return jwt.decode(token, PUBLIC, algorithms=[ALG])
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
