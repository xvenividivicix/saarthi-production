from fastapi import APIRouter
from sqlalchemy import text
from app.deps import get_engine, get_es

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/ready")
def ready():
    ok_db = True
    try:
        with get_engine().connect() as cx:
            cx.execute(text("select 1"))
    except Exception:
        ok_db = False
    es = get_es()
    return {"status": "ok" if ok_db else "degraded", "deps": {"db": ok_db, "es": es is not None}}
