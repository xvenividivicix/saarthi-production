# dependency injection
from elasticsearch import Elasticsearch
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from app.config import settings
from app.services.search import SearchService
from app.services.icd_repo import ICDRepo
from functools import lru_cache

@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(settings.db_url, future=True)

@lru_cache(maxsize=1)
def get_es() -> Elasticsearch | None:
    try:
        es = Elasticsearch(settings.es_url)
        if not es.ping():
            return None
        return es
    except Exception:
        return None

def get_search() -> SearchService:
    return SearchService(get_es(), settings.es_index_icd, get_engine())

def get_icd_repo() -> ICDRepo:
    return ICDRepo(get_engine())
