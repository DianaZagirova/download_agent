#!/usr/bin/env python3
"""
Check for DOI duplicates in the papers database and suggest resolutions
"""
import sys
import os
import sqlite3
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_doi_duplicates(db_path: str):
    """
    Check for duplicate DOIs in the database and provide detailed analysis
    
    Args:
        db_path: Path to the SQLite database
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("="*80)
    print("DOI DUPLICATE ANALYSIS")
    print("="*80)
    print(f"Database: {db_path}\n")
    
    # Get total paper count
    cursor.execute("SELECT COUNT(*) FROM papers")
    total_papers = cursor.fetchone()[0]
    print(f"Total papers in database: {total_papers:,}")
    
    # Count papers with DOIs
    cursor.execute("SELECT COUNT(*) FROM papers WHERE doi IS NOT NULL AND doi != ''")
    papers_with_doi = cursor.fetchone()[0]
    print(f"Papers with DOI: {papers_with_doi:,}")
    print(f"Papers without DOI: {total_papers - papers_with_doi:,}\n")
    
    # Find duplicate DOIs
    cursor.execute("""
        SELECT doi, COUNT(*) as count
        FROM papers
        WHERE doi IS NOT NULL AND doi != ''
        GROUP BY doi
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    """)
    
    duplicates = cursor.fetchall()
    
    if not duplicates:
        print("✅ No DOI duplicates found!")
        print("All DOIs are unique in the database.")
        conn.close()
        return
    
    print(f"⚠️  Found {len(duplicates)} duplicate DOIs")
    print(f"Total duplicate entries: {sum(d['count'] for d in duplicates)}\n")
    
    print("-"*80)
    print("DUPLICATE DOI DETAILS")
    print("-"*80)
    
    all_duplicate_records = []
    
    for dup in duplicates:
        doi = dup['doi']
        count = dup['count']
        
        # Get all papers with this DOI
        cursor.execute("""
            SELECT pmid, pmcid, doi, title, year, journal, 
                   is_full_text_pmc, collection_date, query_id
            FROM papers
            WHERE doi = ?
            ORDER BY collection_date, pmid
        """, (doi,))
        
        records = cursor.fetchall()
        all_duplicate_records.extend(records)
        
        print(f"\n🔍 DOI: {doi}")
        print(f"   Occurrences: {count}")
        print(f"   Records:")
        
        for i, record in enumerate(records, 1):
            print(f"      [{i}] PMID: {record['pmid']}")
            print(f"          PMCID: {record['pmcid'] or 'N/A'}")
            print(f"          Title: {record['title'][:70]}..." if len(record['title']) > 70 else f"          Title: {record['title']}")
            print(f"          Year: {record['year'] or 'N/A'}")
            print(f"          Journal: {record['journal'][:50]}..." if record['journal'] and len(record['journal']) > 50 else f"          Journal: {record['journal'] or 'N/A'}")
            print(f"          Full text: {'Yes' if record['is_full_text_pmc'] else 'No'}")
            print(f"          Collection date: {record['collection_date']}")
            print(f"          Query ID: {record['query_id'] or 'N/A'}")
            print()
    
    print("\n" + "="*80)
    print("RESOLUTION SUGGESTIONS")
    print("="*80)
    
    print("""
The database has duplicate DOIs. This can happen when:
1. Multiple collection runs are performed with overlapping queries
2. Papers are updated/re-collected with same DOI but different PMIDs
3. Data integrity issues in source databases (PubMed/PMC)

RECOMMENDED RESOLUTION STRATEGIES:

Strategy 1: Keep Most Recent Entry (RECOMMENDED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For each duplicate DOI group, keep the entry with the most recent 
collection_date and delete older entries.

Pros: Keeps the most up-to-date data
Cons: May lose some metadata if older entries have additional info

To implement, run:
    python scripts/resolve_doi_duplicates.py --strategy keep-recent


Strategy 2: Keep Entry with Full Text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For each duplicate DOI group, keep the entry that has full text from PMC,
delete others. If none or multiple have full text, fall back to Strategy 1.

Pros: Prioritizes data completeness
Cons: May not always have a clear winner

To implement, run:
    python scripts/resolve_doi_duplicates.py --strategy keep-fulltext


Strategy 3: Merge Duplicates (ADVANCED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Merge all duplicate entries, combining metadata from all sources,
keeping the most complete version of each field.

Pros: Maximum data retention
Cons: Complex, may have conflicting data

To implement, run:
    python scripts/resolve_doi_duplicates.py --strategy merge


Strategy 4: Manual Review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Export duplicate records for manual review and resolution.

To implement, run:
    python scripts/resolve_doi_duplicates.py --strategy export


PREVENTION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
To prevent duplicates in future collections:
1. Add DOI uniqueness constraint to database schema
2. Check for existing DOI before inserting new papers
3. Use UPSERT logic based on DOI instead of just PMID

Note: The current schema uses PMID as PRIMARY KEY, which allows
duplicate DOIs if papers have different PMIDs. Consider modifying
the database schema to enforce DOI uniqueness or use composite keys.
""")
    
    conn.close()


if __name__ == "__main__":
    # Default database path
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'paper_collection', 'data', 'papers.db'
    )
    
    # Allow custom path as argument
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    if not os.path.exists(db_path):
        print(f"❌ Error: Database not found at {db_path}")
        sys.exit(1)
    
    check_doi_duplicates(db_path)
