# FHIR export/import endpoints
from fastapi import APIRouter, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.security import verify_token
from app.models.requests import ExportFHIRReq
from app.services.fhir_builders import build_bundle, summarize_bundle
from fhir.resources.bundle import Bundle

auth = HTTPBearer()
router = APIRouter(prefix="/fhir", tags=["fhir"])

@router.post("/export/bundle")
def export_bundle(req: ExportFHIRReq, cred: HTTPAuthorizationCredentials = Security(auth)):
    verify_token(cred.credentials)
    b = build_bundle(req)
    return b.dict()

@router.post("/import/bundle")
def import_bundle(bundle: dict, cred: HTTPAuthorizationCredentials = Security(auth)):
    verify_token(cred.credentials)
    b = Bundle.parse_obj(bundle)
    return {"valid": True, "summary": summarize_bundle(b)}
