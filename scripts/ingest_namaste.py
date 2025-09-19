# script to ingest NAMASTE mapping
from sqlalchemy import create_engine, text
from app.config import settings  # type: ignore
import csv, os, pathlib

def main():
    csv_path = pathlib.Path("data/namaste_terms.csv")
    if not csv_path.exists():
        print("namaste_terms.csv not found; create data/namaste_terms.csv to ingest."); return
    eng = create_engine(settings.db_url, future=True)
    with eng.begin() as cx:
        cx.exec_driver_sql("CREATE TABLE IF NOT EXISTS namaste_map(namaste_term TEXT, icd_code TEXT, confidence REAL, notes TEXT)")
        with csv_path.open() as f:
            rdr = csv.DictReader(f)
            for row in rdr:
                cx.exec_driver_sql("INSERT INTO namaste_map(namaste_term,icd_code,confidence,notes) VALUES (:t,:c,:p,:n)",
                    {"t":row["namaste_term"],"c":row["icd_code"],"p":float(row.get("confidence",0.9)),"n":row.get("notes","")})
    print("NAMASTE mapping ingested.")

if __name__ == "__main__":
    main()
