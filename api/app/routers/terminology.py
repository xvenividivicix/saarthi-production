# terminology routes
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter(prefix="/terminology", tags=["terminology"])

DATA_DIR = Path(__file__).resolve().parents[3] / "data"

@router.get("/valuesets/{vs_id}")
def get_valueset(vs_id: str):
    fp = DATA_DIR / "valuesets" / f"{vs_id}.json"
    if not fp.exists():
        raise HTTPException(404, "ValueSet not found")
    return json.loads(fp.read_text())

@router.get("/conceptmaps/namaste-to-icd11")
def get_conceptmap():
    fp = DATA_DIR / "conceptmaps" / "namaste-to-icd11.json"
    if not fp.exists():
        return {"resourceType":"ConceptMap","status":"draft","group":[]}
    return json.loads(fp.read_text())
