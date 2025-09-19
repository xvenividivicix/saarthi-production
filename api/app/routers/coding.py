# coding endpoints
from fastapi import APIRouter, Security, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.security import verify_token
from app.models.requests import AutoCodeReq, ValidateReq
from app.models.responses import AutoCodeResp, ValidateResp, Suggestion
from app.deps import get_search, get_icd_repo
from app.services.validators import validate_code

auth = HTTPBearer()
router = APIRouter(prefix="/coding", tags=["coding"])

@router.post("/autocode", response_model=AutoCodeResp)
def autocode(body: AutoCodeReq, cred: HTTPAuthorizationCredentials = Security(auth), search=Depends(get_search)):
    verify_token(cred.credentials)
    suggestions = search.suggest(body.text, body.topK, body.valueSet)
    typed = [Suggestion(**s) for s in suggestions]
    return {"query": body.text, "suggestions": typed}

@router.post("/validate", response_model=ValidateResp)
def validate(body: ValidateReq, cred: HTTPAuthorizationCredentials = Security(auth), repo=Depends(get_icd_repo)):
    verify_token(cred.credentials)
    ok, title = validate_code(repo, body.code)
    return {"valid": ok, "title": title}
