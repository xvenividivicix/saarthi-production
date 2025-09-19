# reindex ES if needed
from elasticsearch import Elasticsearch
import os
INDEX = os.getenv("ES_INDEX_ICD", "icd_tm")
ES_URL = os.getenv("ES_URL", "http://localhost:9200")

def main():
    es = Elasticsearch(ES_URL)
    if not es.ping():
        print("Elasticsearch not reachable; skipping.")
        return
    es.indices.create(index=INDEX, ignore=400, mappings={
        "properties":{
            "code":{"type":"keyword"},
            "title":{"type":"text"},
            "synonyms":{"type":"text"},
            "definition":{"type":"text"},
            "linearization":{"type":"keyword"}
        }})
    print(f"Index ensured: {INDEX}")

if __name__ == "__main__":
    main()
