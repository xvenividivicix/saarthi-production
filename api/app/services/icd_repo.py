# ICD repo logic
from sqlalchemy.engine import Engine
from sqlalchemy import text

class ICDRepo:
    def __init__(self, engine: Engine):
        self.engine = engine
        self._ensure_tables()

    def _ensure_tables(self):
        with self.engine.begin() as cx:
            cx.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS icd_concept(
              id TEXT PRIMARY KEY,
              code TEXT,
              title TEXT,
              definition TEXT,
              linearization TEXT,
              last_updated TEXT
            );""")
            cx.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS icd_synonym(
              concept_id TEXT,
              term TEXT,
              lang TEXT,
              weight REAL DEFAULT 1.0
            );""")

    def get(self, code: str):
        with self.engine.begin() as cx:
            row = cx.exec_driver_sql("SELECT id, code, title, definition, linearization FROM icd_concept WHERE code=:c", {"c":code}).fetchone()
            if not row: return None
            return {"id": row[0], "code": row[1], "title": row[2], "definition": row[3], "linearization": row[4]}
