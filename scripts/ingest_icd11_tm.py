# Ingest ICD-11 Traditional Medicine (TM in MMS Chapter 26: S* codes) into DB + Elasticsearch
# Strategy:
#   1) Traverse MMS Chapter 26 via official chapter endpoint and follow 'child' links
#   2) If nothing found, fallback to probing S* code space (SA..SJ), optionally small test range
#   3) Optional manual WHO entity seeds + optional search endpoint fallback
#
# Environment variables used (set in .env and passed to 'worker' service):
#   DB_URL=postgresql+psycopg2://saarthi:saarthi@db:5432/saarthi
#   ES_URL=http://es:9200
#   ES_INDEX_ICD=icd_tm
#   ICD_API_BASE=https://id.who.int/icd/release/11
#   ICD_RELEASE_ID=latest            # or '2024-01' etc.
#   ICD_CLIENT_ID=...
#   ICD_CLIENT_SECRET=...
#   SMALL_PROBE=true                 # optional, limits probe to SA00–SA49 (faster test)
#   ICD_SEARCH_URL=                  # optional WHO search endpoint for experiments
#   TM_SEED_IDS_FILE=data/seeds/tm_entity_ids.txt   # optional manual seed URIs

import os
import time
from typing import Dict, Any, List, Iterable, Set, Optional

import httpx
from tqdm import tqdm
from sqlalchemy import create_engine, text
from elasticsearch import Elasticsearch, helpers

# ---------- ENV ----------
SEED_ONLY = os.getenv("SEED_ONLY", "0") == "1"

DB_URL        = os.getenv("DB_URL", "sqlite:///./data/app.db")
ES_URL        = os.getenv("ES_URL", "http://es:9200")
ES_INDEX      = os.getenv("ES_INDEX_ICD", "icd_tm")

ICD_BASE      = os.getenv("ICD_API_BASE", "https://id.who.int/icd/release/11").rstrip("/")
ICD_RELEASE   = os.getenv("ICD_RELEASE_ID", "latest")  # 'latest' or 'YYYY-MM'

CLIENT_ID     = os.getenv("ICD_CLIENT_ID")
CLIENT_SECRET = os.getenv("ICD_CLIENT_SECRET")

SMALL_PROBE   = os.getenv("SMALL_PROBE", "").lower() in {"1", "true", "yes", "y"}
ICD_SEARCH_URL = os.getenv("ICD_SEARCH_URL", "").strip()
SEED_IDS_FILE  = os.getenv("TM_SEED_IDS_FILE", "data/seeds/tm_entity_ids.txt").strip()

TOKEN_URL     = "https://icdaccessmanagement.who.int/connect/token"  # WHO OAuth2

# ---------- AUTH ----------
def fetch_token() -> str:
    if not CLIENT_ID or not CLIENT_SECRET:
        raise SystemExit("ICD_CLIENT_ID / ICD_CLIENT_SECRET missing in environment.")
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "icdapi_access",
    }
    r = httpx.post(TOKEN_URL, data=data, timeout=30)
    r.raise_for_status()
    token = r.json()["access_token"]
    print("✅ Token fetched successfully.")
    return token

def hclient(token: str) -> httpx.Client:
    # v2 API requires API-Version: v2
    return httpx.Client(
        timeout=40,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "API-Version": "v2",
            # "Accept-Language": "en",  # optionally force English
        },
    )

# ---------- HTTP HELPERS ----------
def get_json(c: httpx.Client, url: str, params: Optional[dict] = None) -> Dict[str, Any]:
    for attempt in range(5):
        resp = c.get(url, params=params)
        if resp.status_code == 429:
            # Gentle backoff on rate limit
            time.sleep(1.0 * (attempt + 1))
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    return {}

# ---------- MMS CHAPTER 26 TRAVERSAL ----------
def fetch_mms_chapter_tm_entities(c: httpx.Client) -> List[Dict[str, Any]]:
    """
    Traverse MMS Chapter 26 (Traditional Medicine Conditions) and collect entities
    whose 'theCode' starts with 'S'.
    """
    base = f"{ICD_BASE}/{ICD_RELEASE}/mms"
    chapter_url = f"{base}/chapter/26"
    print(f"🔎 Targeting MMS; release={ICD_RELEASE}, base={ICD_BASE}")
    print(f"🔎 Traversing MMS Chapter 26: {chapter_url}")

    try:
        chapter = get_json(c, chapter_url)
    except httpx.HTTPStatusError as e:
        print(f"⚠️ MMS chapter fetch failed: {e.response.status_code}")
        return []

    results: List[Dict[str, Any]] = []
    stack: List[Dict[str, Any]] = [chapter]
    seen_urls: Set[str] = set()

    def ent_uri(n: Dict[str, Any]) -> Optional[str]:
        return (n.get("@id") or n.get("id") or n.get("uri") or n.get("url"))

    with tqdm(total=0, unit="nodes", desc="🌿 Traversing Chapter 26", leave=False) as pbar:
        while stack:
            node = stack.pop()
            uri = ent_uri(node)
            # Resolve stub to full entity if we have a resolvable URI and haven’t seen it
            if uri and uri not in seen_urls:
                seen_urls.add(uri)
                try:
                    node = get_json(c, uri)
                except httpx.HTTPStatusError:
                    pass

            # Collect S* codes (TM in MMS)
            code = node.get("theCode") or node.get("code")
            if isinstance(code, str) and code.startswith("S"):
                results.append(node)

            # Traverse children
            for ch in node.get("child") or []:
                stack.append(ch)

            pbar.total = len(seen_urls)
            pbar.update(0)

    print(f"📄 Chapter traversal collected {len(results)} TM entities (S*).")
    return results

# ---------- MMS PROBE (SA..SJ) ----------
def _gen_sa_sa49() -> Iterable[str]:
    # Small test: SA00..SA49
    for i in range(0, 50):
        yield f"SA{i:02d}"

def _gen_sa_sj_full() -> Iterable[str]:
    # Larger probe space: SA00..SAZZ, SB..SJ similarly (broad; keep pace slow)
    alnum = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for first in "ABCDEFGHIJ":  # SA..SJ
        for c2 in alnum:
            yield f"S{first}{c2}"
        for c2 in alnum:
            for c3 in alnum:
                yield f"S{first}{c2}{c3}"

def fetch_mms_tm_entities(c: httpx.Client) -> List[Dict[str, Any]]:
    base = f"{ICD_BASE}/{ICD_RELEASE}/mms"
    print(f"🔎 Targeting MMS; release={ICD_RELEASE}, base={ICD_BASE}")
    print(f"🔎 Scanning MMS for TM (S*) codes under: SA..SJ (broad probe)")

    letters_first = list("ABCDEFGHIJ")  # SA..SJ
    alnum = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def generate_codes():
        for L in letters_first:
            for c2 in alnum:
                yield f"S{L}{c2}"
            for c2 in alnum:
                for c3 in alnum:
                    yield f"S{L}{c2}{c3}"

    found = []
    seen = set()
    codes = list(generate_codes())

    for i, code in enumerate(tqdm(codes, desc="🔍 Probing SA..SJ", mininterval=1.0)):
        url = f"{base}/{code}"
        try:
            ent = get_json(c, url)
            the_code = ent.get("theCode") or ent.get("code")
            if isinstance(the_code, str) and the_code.startswith("S") and code not in seen:
                found.append(ent)
                seen.add(code)
                if len(found) % 20 == 0:
                    print(f"✅ Fetched {len(found)} entities so far...")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                continue  # expected
            elif e.response.status_code == 429:
                print("⏳ Rate limit hit. Sleeping 2s.")
                time.sleep(2)
        except Exception as e:
            print(f"⚠️ Unexpected error: {e}")
        time.sleep(0.02)

    print(f"📄 Fetched {len(found)} raw MMS entities (S*).")
    return found


# ---------- OPTIONAL: MANUAL SEEDS ----------
def load_seed_entity_ids() -> List[str]:
    if not os.path.exists(SEED_IDS_FILE):
        return []
    ids: List[str] = []
    with open(SEED_IDS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            u = line.strip()
            if u and not u.startswith("#"):
                ids.append(u.replace("http://", "https://"))
    return ids

def fetch_entities_from_seeds(c: httpx.Client, ids: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, uri in enumerate(ids, 1):
        try:
            ent = get_json(c, uri)
            print(f'✅ {i}/{len(ids)} OK: {uri}')
            out.append(ent)
        except httpx.HTTPStatusError as e:
            code = e.response.status_code if e.response is not None else 'ERR'
            print(f'❌ {i}/{len(ids)} {code}: {uri}')
        if i % 50 == 0:
            print(f"\t🌱 fetched {i}/{len(ids)} seeds...")
        time.sleep(0.02)
    print(f"🌱 Seed fallback fetched {len(out)} entities.")
    return out


# ---------- OPTIONAL: SEARCH (CONFIGURABLE) ----------
def try_search_endpoint(c: httpx.Client) -> List[Dict[str, Any]]:
    if not ICD_SEARCH_URL:
        return []
    print(f"🔎 Trying configured search endpoint: {ICD_SEARCH_URL}")
    queries = ["Ayurveda", "Unani", "Siddha", "Traditional Medicine", "acupuncture", "dosha", "prakriti"]
    seen: Set[str] = set()
    results: List[Dict[str, Any]] = []
    for q in queries:
        params = {"query": q, "useFlexisearch": True, "pageSize": 200}
        try:
            data = get_json(c, ICD_SEARCH_URL, params=params)
            items = data.get("destinationEntities") or data.get("items") or []
            for it in items:
                uri = it.get("@id") or it.get("id") or it.get("uri") or it.get("url")
                if not uri or uri in seen:
                    continue
                seen.add(uri)
                try:
                    ent = get_json(c, uri)
                    results.append(ent)
                except httpx.HTTPStatusError:
                    pass
        except httpx.HTTPStatusError:
            pass
        time.sleep(0.1)
    print(f"🔎 Search fallback fetched {len(results)} entities.")
    return results

# ---------- NORMALIZE ----------
def normalize_concepts(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    concepts: List[Dict[str, Any]] = []
    for ent in entities:
        ent_id = ent.get("@id") or ent.get("id") or ent.get("uri") or ent.get("url")
        code = ent.get("theCode") or ent.get("code")
        title = ent.get("title")
        title_val = title.get("@value") if isinstance(title, dict) else title
        definition = ent.get("definition")
        def_val = definition.get("@value") if isinstance(definition, dict) else definition
        synonyms = ent.get("synonym") or ent.get("synonyms") or []

        if isinstance(code, str) and code.startswith("S") and ent_id:
            syn_terms = []
            for s in synonyms:
                lbl = s.get("label") or s.get("@value")
                if lbl:
                    syn_terms.append({"label": lbl, "lang": s.get("lang", "en")})

            concepts.append({
                "id": ent_id.replace("http://", "https://"),
                "code": code,
                "title": title_val or "",
                "definition": def_val or None,
                "synonyms": syn_terms,
                "linearization": f"mms:{ICD_RELEASE}",
            })
    print(f"🧠 Normalized {len(concepts)} TM concepts.")
    return concepts

# ---------- DB ----------
def ensure_tables(engine):
    with engine.begin() as cx:
        cx.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS icd_concept(
              id TEXT PRIMARY KEY,
              code TEXT,
              title TEXT,
              definition TEXT,
              linearization TEXT,
              last_updated TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        cx.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS icd_synonym(
              concept_id TEXT,
              term TEXT,
              lang TEXT,
              weight REAL DEFAULT 1.0,
              linearization TEXT
            );
        """)

def upsert_to_db(concepts: List[Dict[str, Any]]):
    if not concepts:
        print("⚠️ No concepts to upsert. Skipping DB operations.")
        return
    eng = create_engine(DB_URL, future=True)
    ensure_tables(eng)
    with eng.begin() as conn:
        conn.exec_driver_sql("DELETE FROM icd_synonym WHERE linearization LIKE 'mms:%'")
        conn.exec_driver_sql("DELETE FROM icd_concept  WHERE linearization LIKE 'mms:%'")

        for c in concepts:
            conn.execute(
                text("""INSERT INTO icd_concept (id, code, title, definition, linearization)
                        VALUES (:id, :code, :title, :definition, :lin)"""),
                dict(
                    id=c["id"],
                    code=c["code"],
                    title=c["title"],
                    definition=c["definition"],
                    lin=c["linearization"]
                )
            )
            for syn in c["synonyms"]:
                conn.execute(
                    text("""INSERT INTO icd_synonym (concept_id, term, lang, weight, linearization)
                            VALUES (:cid, :term, :lang, :w, :lin)"""),
                    dict(
                        cid=c["id"],
                        term=syn["label"],
                        lang=syn.get("lang", "en"),
                        w=1.0,
                        lin=c["linearization"]
                    )
                )
    print(f"✅ DB upserted {len(concepts)} TM concepts.")

# ---------- ES ----------
def bulk_actions(concepts: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    for c in concepts:
        yield {
            "_index": ES_INDEX,
            "_id": c["id"],
            "_source": {
                "code": c["code"],
                "title": c["title"],
                "definition": c["definition"],
                "synonyms": [s["label"] for s in c["synonyms"]],
                "linearization": c["linearization"],
            },
        }

def index_to_es(concepts: List[Dict[str, Any]]):
    es = Elasticsearch(ES_URL)
    if es.indices.exists(index=ES_INDEX):
        es.indices.delete(index=ES_INDEX)
    es.indices.create(index=ES_INDEX)
    helpers.bulk(es, bulk_actions(concepts), stats_only=True, request_timeout=180)
    print(f"📦 Indexed {len(concepts)} documents into ES index '{ES_INDEX}'.")

# ---------- MAIN ----------
def main():
    print("🔐 Fetching ICD-11 API token...")
    token = fetch_token()
    client = hclient(token)

    # --- SEEDS ONLY (temporary) ---
    seed_ids = load_seed_entity_ids()
    if not seed_ids:
        raise SystemExit("❌ No seed IDs found at data/seeds/tm_entity_ids.txt")

    print(f"🌱 Using manual seed IDs: {len(seed_ids)}")
    all_entities = fetch_entities_from_seeds(client, seed_ids)

    # Normalize + persist
    concepts = normalize_concepts(all_entities)
    upsert_to_db(concepts)
    index_to_es(concepts)


if __name__ == "__main__":
    main()

