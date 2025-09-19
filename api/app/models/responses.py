# response models
from pydantic import BaseModel
from typing import List, Optional

class Suggestion(BaseModel):
    code: str
    display: str
    system: str
    score: float
    linearization: str | None = None

class AutoCodeResp(BaseModel):
    query: str
    suggestions: list[Suggestion]

class ValidateResp(BaseModel):
    valid: bool
    title: str | None = None
    linearization: str | None = None
