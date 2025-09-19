# main app entry (to be completed)
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings
from app.logging import configure_logging
from app.routers import auth, coding, terminology, fhirio, health

configure_logging()

app = FastAPI(title="SAARTHI (minimal)")

@app.get("/ping")
def ping():
    return {"ok": True}

# CORS
origins = [o for o in settings.cors_allowed_origins.split(",") if o]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET","POST","OPTIONS"],
    allow_headers=["Authorization","Content-Type"]
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_rps}/second"])  # type: ignore
app.state.limiter = limiter

@app.middleware("http")
async def add_rate_headers(request: Request, call_next):
    response = await call_next(request)
    return response

# Routers
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(coding.router, prefix=settings.api_prefix)
app.include_router(terminology.router, prefix=settings.api_prefix)
app.include_router(fhirio.router, prefix=settings.api_prefix)
app.include_router(health.router, prefix=settings.api_prefix)


