#!/usr/bin/env python3
"""
Script to identify failed paper retrievals by comparing search results with database
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import PaperDatabase
from src.pubmed_extractor import search_pubmed
from src.config import DATABASE_PATH

def check_failed_papers(query: str, db_path: str = None):
    """
    Compare search results with database to find failed retrievals.
    
    Args:
        query: The PubMed query that was used
        db_path: Path to database (optional, uses default if not provided)
    """
    print("="*60)
    print("FAILED PAPER RETRIEVAL CHECKER")
    print("="*60)
    
    # Initialize database
    if db_path:
        db = PaperDatabase(db_path=db_path)
    else:
        db = PaperDatabase()
    
    print(f"\nUsing database: {db.db_path}")
    
    # Search PubMed to get the original list of PMIDs
    print(f"\nSearching PubMed with query...")
    pmid_list = search_pubmed(query, max_results=50000)
    
    if not pmid_list:
        print("No papers found in search. Exiting.")
        return
    
    print(f"Found {len(pmid_list)} papers in PubMed search")
    
    # Get all PMIDs from database
    cursor = db.conn.cursor()
    cursor.execute("SELECT pmid FROM papers")
    db_pmids = set(row[0] for row in cursor.fetchall())
    
    print(f"Found {len(db_pmids)} papers in database")
    
    # Find missing PMIDs (failed retrievals)
    search_pmids = set(pmid_list)
    failed_pmids = search_pmids - db_pmids
    
    print(f"\n{'='*60}")
    print(f"FAILED RETRIEVALS: {len(failed_pmids)} papers")
    print(f"{'='*60}")
    
    if failed_pmids:
        print("\nFailed PMIDs:")
        for pmid in sorted(failed_pmids):
            print(f"  - PMID: {pmid}")
            print(f"    URL: https://pubmed.ncbi.nlm.nih.gov/{pmid}/")
        
        # Save to file
        output_file = os.path.join(os.path.dirname(db.db_path), 'failed_pmids.txt')
        with open(output_file, 'w') as f:
            f.write(f"Failed PubMed Retrievals: {len(failed_pmids)} papers\n")
            f.write(f"Query: {query}\n")
            f.write(f"{'='*60}\n\n")
            for pmid in sorted(failed_pmids):
                f.write(f"PMID: {pmid}\n")
                f.write(f"URL: https://pubmed.ncbi.nlm.nih.gov/{pmid}/\n\n")
        
        print(f"\n✓ Failed PMIDs saved to: {output_file}")
        
        # Try to get basic info about failed papers
        print(f"\n{'='*60}")
        print("Attempting to retrieve basic info for failed papers...")
        print(f"{'='*60}\n")
        
        from src.pubmed_extractor import extract_pubmed_metadata
        
        for pmid in sorted(list(failed_pmids)[:5]):  # Check first 5
            print(f"Checking PMID {pmid}...")
            metadata = extract_pubmed_metadata(pmid)
            if metadata:
                print(f"  ✓ Title: {metadata.title[:80]}...")
                print(f"  ✓ Year: {metadata.year}")
            else:
                print(f"  ✗ Could not retrieve metadata")
            print()
        
        if len(failed_pmids) > 5:
            print(f"(Showing first 5 of {len(failed_pmids)} failed papers)")
    else:
        print("\n✓ No failed retrievals found! All papers were successfully processed.")
    
    db.close()
    print(f"\n{'='*60}")


if __name__ == "__main__":
    # Use the same query from run_full.py
    query = """
(
aging[Title] OR ageing[Title])
 AND ( theory[Title] OR theories[Title] OR hypothesis[Title] OR hypotheses[Title] OR paradigm[Title] OR paradigms[Title])
)
NOT
(Case Reports[Publication Type] OR "case report"[Title] OR "case reports"[Title] OR Clinical Trial[Publication Type] OR "protocol"[Title] OR "conference"[Title] OR "meeting"[Title] OR "well-being"[TI] OR "successful aging"[TI] OR "successful ageing"[TI] OR "ovarian"[TI] OR "liver"[TI] OR "kidne*"[TI] OR "skin"[TI] OR "religion"[TI] OR "enjoyment"[TI] OR "disease hypothesis"[TI] OR "healthy aging"[TI] OR "healthy ageing"[TI] OR "menopause"[TI] 
)
"""
    
    # If you used a custom output directory, specify it here
    # Example: check_failed_papers(query, db_path="/path/to/custom/papers.db")
    check_failed_papers(query)
