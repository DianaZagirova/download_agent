#!/usr/bin/env python3
import sqlite3
import json
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from Bio import Entrez

# === CONFIG ===
DB_PATH = "paper_collection/data/papers.db"
OUTPUT_JSON = "paper_collection/data/doi_fixes_candidates.json"
# Set your contact email and optionally API key
Entrez.email = "diana.z@insilicomedicine.com"
Entrez.api_key = "9f5d0d5238d7eb65e0526c84d79a5b945d08"
SLEEP_BETWEEN_CALLS_SEC = 0.34

# Suspicious DOI heuristics:
# - Not matching a simple DOI shape 10.xxxx/...
# - Starts with slash or contains XML or looks like publisher path fragments
VALID_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)

def is_suspicious_doi(doi: str) -> bool:
    if not doi:
        return False
    # Normalize first to handle prefixes like https://doi.org/ and doi:
    s = normalize_doi_text(doi).strip()

    # If it matches a standard DOI shape, consider it OK
    if VALID_DOI_RE.match(s):
        return False

    # Clear junk/path-like signatures
    if s.startswith("/") or s.endswith(".xml"):
        return True
    if "/issue-" in s or "/ahead-of-print/" in s:
        return True
    if s.startswith("00/"):
        return True
    if " " in s:
        return True

    # Fallback: anything not matching DOI regex is suspicious
    return True

def normalize_doi_text(s: str) -> str:
    s = s.strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if s.lower().startswith(prefix):
            return s[len(prefix):].strip()
    return s

def fetch_doi_from_pmid(pmid: str) -> Optional[str]:
    """Fetch DOI for a PMID using Entrez and return the ArticleIdList entry with IdType='doi'."""
    try:
        h = Entrez.efetch(db="pubmed", id=pmid, retmode="xml")
        rec = Entrez.read(h)
        h.close()
    except Exception as e:
        print(f"Error efetch PMID {pmid}: {e}")
        return None

    for article in rec.get("PubmedArticle", []):
        pubmed_data = article.get("PubmedData", {})
        for id_item in pubmed_data.get("ArticleIdList", []):
            id_str = str(id_item)
            id_type = id_item.attributes.get("IdType") if hasattr(id_item, "attributes") else None
            if id_type and id_type.lower() == "doi":
                return normalize_doi_text(id_str)
    return None

def main():
    db_path = Path(DB_PATH)
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Pull candidates to check; filter down in Python via regex for precision
    cur.execute("SELECT pmid, doi, title FROM papers WHERE doi IS NOT NULL")
    rows = cur.fetchall()

    candidates: List[Dict[str, Any]] = []
    for row in rows:
        pmid = str(row["pmid"]) if row["pmid"] is not None else None
        doi = row["doi"]
        title = row["title"]

        if doi and is_suspicious_doi(doi):
            candidates.append({
                "pmid": pmid,
                "old_doi": doi,
                "old_doi_normalized": normalize_doi_text(doi),
                "title": title
            })

    print(f"Found {len(candidates)} suspicious DOI entries to check via Entrez")
    print(candidates[:19])

    fixes: List[Dict[str, Any]] = []

    for idx, item in enumerate(candidates, 1):
        pmid = item["pmid"]
        old_doi = item["old_doi"]

        new_doi = None
        reason = None

        if pmid:
            new_doi = fetch_doi_from_pmid(pmid)
            reason = "entrez_articleid_idtype_doi" if new_doi else "no_doi_found_for_pmid"
        else:
            reason = "no_pmid_available"

        if new_doi and new_doi != old_doi:
            fixes.append({
                "pmid": pmid,
                "old_doi": old_doi,
                "new_doi": new_doi,
                "reason": reason,
            })

        if idx % 25 == 0:
            print(f"Processed {idx}/{len(candidates)}")
        time.sleep(SLEEP_BETWEEN_CALLS_SEC)

    out_path = Path(OUTPUT_JSON)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump({
            "total_candidates": len(candidates),
            "total_with_proposed_fix": len(fixes),
            "fixes": fixes
        }, f, indent=2, ensure_ascii=False)

    print(f"✓ Wrote proposed DOI fixes to {out_path}")
    print("No database changes were made. Review JSON and apply manually if desired.")

if __name__ == "__main__":
    main()