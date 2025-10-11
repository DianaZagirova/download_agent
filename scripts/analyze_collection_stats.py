#!/usr/bin/env python3
"""
Analyze collection statistics and identify issues
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import PaperDatabase
from src.config import DATABASE_PATH

def analyze_collection(db_path: str = None):
    """
    Analyze collection statistics and show detailed breakdown.
    
    Args:
        db_path: Path to database (optional)
    """
    print("="*60)
    print("COLLECTION ANALYSIS")
    print("="*60)
    
    # Initialize database
    if db_path:
        db = PaperDatabase(db_path=db_path)
    else:
        db = PaperDatabase()
    
    print(f"\nDatabase: {db.db_path}\n")
    
    cursor = db.conn.cursor()
    
    # Get collection run stats
    cursor.execute("""
        SELECT * FROM collection_runs 
        ORDER BY id DESC 
        LIMIT 1
    """)
    run = cursor.fetchone()
    
    if run:
        print("Latest Collection Run:")
        print(f"  Query: {run['query'][:80]}...")
        print(f"  Total found: {run['total_found']}")
        print(f"  Total processed: {run['total_processed']}")
        print(f"  Failed PubMed: {run['failed_pubmed']}")
        print(f"  With full text: {run['with_full_text']}")
        print(f"  With OpenAlex: {run['with_openalex']}")
        
        # Calculate what failed
        expected = run['total_found']
        processed = run['total_processed']
        failed = run['failed_pubmed']
        
        print(f"\n{'='*60}")
        print("FAILURE ANALYSIS")
        print(f"{'='*60}")
        print(f"Expected papers: {expected}")
        print(f"Successfully processed: {processed}")
        print(f"Failed retrievals: {failed}")
        print(f"Missing (not processed): {expected - processed - failed}")
    
    # Get papers without full text
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM papers 
        WHERE is_full_text_pmc = 0 OR is_full_text_pmc IS NULL
    """)
    no_fulltext = cursor.fetchone()['count']
    
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM papers 
        WHERE is_full_text_pmc = 1
    """)
    with_fulltext = cursor.fetchone()['count']
    
    print(f"\n{'='*60}")
    print("FULL TEXT AVAILABILITY")
    print(f"{'='*60}")
    print(f"Papers with full text: {with_fulltext}")
    print(f"Papers without full text: {no_fulltext}")
    print(f"Full text rate: {with_fulltext/(with_fulltext+no_fulltext)*100:.1f}%")
    
    # Check failed DOIs table
    cursor.execute("SELECT COUNT(*) as count FROM failed_dois")
    failed_dois_count = cursor.fetchone()['count']
    
    if failed_dois_count > 0:
        print(f"\n{'='*60}")
        print("PAPERS WITHOUT PMC FULL TEXT")
        print(f"{'='*60}")
        print(f"Total: {failed_dois_count} papers")
        
        # Show some examples
        cursor.execute("""
            SELECT doi, pmid, reason 
            FROM failed_dois 
            LIMIT 10
        """)
        print("\nExamples (first 10):")
        for row in cursor.fetchall():
            print(f"  PMID: {row['pmid']}")
            print(f"  DOI: {row['doi']}")
            print(f"  Reason: {row['reason']}")
            print()
    
    # OpenAlex statistics
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM papers 
        WHERE openalex_retrieved = 1
    """)
    with_openalex = cursor.fetchone()['count']
    
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM papers 
        WHERE doi IS NOT NULL AND doi != ''
    """)
    with_doi = cursor.fetchone()['count']
    
    print(f"\n{'='*60}")
    print("OPENALEX ENRICHMENT")
    print(f"{'='*60}")
    print(f"Papers with DOI: {with_doi}")
    print(f"Papers with OpenAlex data: {with_openalex}")
    if with_doi > 0:
        print(f"OpenAlex success rate: {with_openalex/with_doi*100:.1f}%")
    
    # Papers by year
    cursor.execute("""
        SELECT year, COUNT(*) as count 
        FROM papers 
        WHERE year IS NOT NULL AND year != ''
        GROUP BY year 
        ORDER BY year DESC 
        LIMIT 10
    """)
    
    print(f"\n{'='*60}")
    print("PAPERS BY YEAR (Top 10)")
    print(f"{'='*60}")
    for row in cursor.fetchall():
        print(f"  {row['year']}: {row['count']} papers")
    
    # Top journals
    cursor.execute("""
        SELECT journal, COUNT(*) as count 
        FROM papers 
        WHERE journal IS NOT NULL AND journal != ''
        GROUP BY journal 
        ORDER BY count DESC 
        LIMIT 10
    """)
    
    print(f"\n{'='*60}")
    print("TOP JOURNALS")
    print(f"{'='*60}")
    for row in cursor.fetchall():
        print(f"  {row['count']:3d} papers - {row['journal'][:60]}")
    
    db.close()
    print(f"\n{'='*60}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze paper collection statistics')
    parser.add_argument('--db', type=str, help='Path to database file', default=None)
    
    args = parser.parse_args()
    
    analyze_collection(db_path=args.db)
