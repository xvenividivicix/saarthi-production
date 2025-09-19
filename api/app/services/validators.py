# validate codes
from app.services.icd_repo import ICDRepo

def validate_code(repo: ICDRepo, code: str) -> tuple[bool, str | None]:
    c = repo.get(code)
    if not c: 
        return False, None
    return True, c.get("title")
