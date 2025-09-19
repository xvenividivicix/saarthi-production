# auth routes
from fastapi import APIRouter, HTTPException, Form
from app.security import create_token

router = APIRouter(prefix="/auth", tags=["auth"])

# Simple client store (replace with DB or config in production)
CLIENTS = {"demo-client-id": "demo-client-secret"}

@router.post("/token")
def token(client_id: str = Form(...), client_secret: str = Form(...), scope: str = Form(default="read:codes")):
    if CLIENTS.get(client_id) != client_secret:
        raise HTTPException(status_code=401, detail="invalid client credentials")
    return {"access_token": create_token(client_id, scope.split()), "token_type": "bearer"}
