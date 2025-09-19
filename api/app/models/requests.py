# request models
from pydantic import BaseModel, Field
from typing import Optional, List

class AutoCodeReq(BaseModel):
    text: str
    valueSet: Optional[str] = None
    topK: int = 10
    lang: str = "en"

class ValidateReq(BaseModel):
    code: str
    system: str = "http://id.who.int/icd/release/11"

class PatientIn(BaseModel):
    id: str | None = None
    name: str
    gender: str | None = None
    birthDate: str | None = None

class CodeItem(BaseModel):
    text: str | None = None
    code: str
    display: str
    system: str = "http://id.who.int/icd/release/11"
    performedDateTime: str | None = None

class ExportFHIRReq(BaseModel):
    patient: PatientIn
    encounter: dict | None = None
    conditions: List[CodeItem] | None = None
    procedures: List[CodeItem] | None = None
