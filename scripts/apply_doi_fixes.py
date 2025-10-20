#!/usr/bin/env python3
import argparse
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Tuple

DB_PATH_DEFAULT = "paper_collection/data/papers.db"
FIXES_JSON_DEFAULT = "paper_collection/data/doi_fixes_candidates.json"
BACKUP_SUFFIX = ".backup_before_doi_fix"

def load_fixes(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    fixes = data.get("fixes", [])
    # Keep only entries with all fields
    out = []
    for fx in fixes:
        pmid = fx.get("pmid")
        old_doi = fx.get("old_doi")
        new_doi = fx.get("new_doi")
        if pmid and old_doi and new_doi:
            out.append({"pmid": str(pmid), "old_doi": old_doi, "new_doi": new_doi})
    return out

def plan_updates(conn: sqlite3.Connection, fixes: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    cur = conn.cursor()
    applicable = []
    already_ok = []
    missing = []

    for fx in fixes:
        pmid = fx["pmid"]
        old_doi = fx["old_doi"]
        new_doi = fx["new_doi"]

        cur.execute("SELECT doi FROM papers WHERE pmid = ? LIMIT 1", (pmid,))
        row = cur.fetchone()
        if not row:
            missing.append({**fx, "status": "pmid_not_found"})
            continue

        current = row[0]
        if current == new_doi:
            already_ok.append({**fx, "status": "already_new"})
        elif current == old_doi:
            applicable.append(fx)
        else:
            missing.append({**fx, "status": f"unexpected_current:{current}"})

    return applicable, already_ok, missing

def apply_updates(conn: sqlite3.Connection, updates: List[Dict[str, Any]]) -> int:
    cur = conn.cursor()
    total_updated = 0
    for fx in updates:
        pmid = fx["pmid"]
        old_doi = fx["old_doi"]
        new_doi = fx["new_doi"]
        cur.execute(
            "UPDATE papers SET doi = ? WHERE pmid = ? AND doi = ?",
            (new_doi, pmid, old_doi),
        )
        total_updated += cur.rowcount
    conn.commit()
    return total_updated

def main():
    ap = argparse.ArgumentParser(description="Apply DOI fixes from JSON to SQLite DB (safe, explicit pairs only).")
    ap.add_argument("--db", default=DB_PATH_DEFAULT, help="Path to SQLite DB (papers.db)")
    ap.add_argument("--json", default=FIXES_JSON_DEFAULT, help="Path to fixes JSON (doi_fixes_candidates.json)")
    ap.add_argument("--apply", action="store_true", help="Actually update the DB (otherwise dry-run)")
    ap.add_argument("--backup", action="store_true", help="Create a backup of the DB before applying")
    args = ap.parse_args()

    db_path = Path(args.db)
    json_path = Path(args.json)

    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return
    if not json_path.exists():
        print(f"Fixes JSON not found: {json_path}")
        return

    fixes = load_fixes(json_path)
    print(f"Loaded {len(fixes)} fix candidates from {json_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Make a deterministic plan
    applicable, already_ok, missing = plan_updates(conn, fixes)

    print("\nPlan summary (dry-run):")
    print(f"- Applicable (current == old_doi, will update): {len(applicable)}")
    print(f"- Already OK (current == new_doi, no change): {len(already_ok)}")
    print(f"- Missing/Unexpected (pmid not found or current != old_doi): {len(missing)}")

    # Show a few examples for sanity
    print("\nExamples (up to 10) of applicable updates:")
    for fx in applicable[:10]:
        print(f"  PMID {fx['pmid']}: {fx['old_doi']} -> {fx['new_doi']}")

    print("\nExamples (up to 5) of missing/unexpected:")
    for fx in missing[:5]:
        print(f"  PMID {fx['pmid']}: status={fx.get('status')}")

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to write changes. No other DOIs will be affected.")
        conn.close()
        return

    # Optional backup
    if args.backup:
        backup_path = db_path.with_suffix(db_path.suffix + BACKUP_SUFFIX)
        shutil.copy2(db_path, backup_path)
        print(f"Backup created at: {backup_path}")

    # Apply only explicit pairs
    updated_count = apply_updates(conn, applicable)
    conn.close()

    print(f"\nApplied updates: {updated_count} rows updated.")
    print("Only rows matching (pmid AND old_doi) were touched. No other DOIs were affected.")

if __name__ == "__main__":
    main()