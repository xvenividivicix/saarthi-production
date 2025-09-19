# search logic with ES
from typing import List
from elasticsearch import Elasticsearch
from sqlalchemy.engine import Engine

class SearchService:
    def __init__(self, es: Elasticsearch | None, index: str, engine: Engine):
        self.es = es
        self.index = index
        self.engine = engine

    def suggest(self, text: str, top_k: int = 10, value_set: str | None = None):
        text = (text or '').strip()
        if not text:
            return []

        # Prefer Elasticsearch
        if self.es is not None:
            try:
                q = {
                    "size": top_k,
                    "query": {
                        "multi_match": {
                            "query": text,
                            "fields": ["title^3","synonyms^2","definition"]
                        }
                    }
                }
                res = self.es.search(index=self.index, body=q)
                out=[]
                for hit in res["hits"]["hits"]:
                    src = hit["_source"]
                    out.append({
                        "code": src.get("code"),
                        "display": src.get("title"),
                        "system": "http://id.who.int/icd/release/11",
                        "score": hit.get("_score", 0.0),
                        "linearization": src.get("linearization")
                    })
                if out:
                    return out
            except Exception:
                pass

        # Fallback: simple LIKE search on DB if ES unavailable
        with self.engine.begin() as cx:
            rows = cx.exec_driver_sql(
                "SELECT code, title FROM icd_concept WHERE title LIKE :q LIMIT :k",
                {"q": f"%{text}%", "k": top_k}
            ).fetchall()
        return [{
            "code": r[0], "display": r[1], "system": "http://id.who.int/icd/release/11", "score": 1.0
        } for r in rows]
