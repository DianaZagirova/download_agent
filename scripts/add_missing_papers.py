#!/usr/bin/env python3
"""
Script to manually add papers from data/add_missing.py to the database
"""
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import PaperMetadata
from src.database import PaperDatabase

# Import the data from add_missing.py
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data'))
from add_missing import dois

# ============================================================================
# CONFIGURATION
# ============================================================================

DATABASE_PATH = "paper_collection/data/papers.db"  # Relative to project root
QUERY_DESCRIPTION = "Manually added papers"

# ============================================================================
# MAIN SCRIPT
# ============================================================================

def main():
    """Add missing papers to the database"""
    
    # Get absolute path to database
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(project_root, DATABASE_PATH)
    
    print("="*60)
    print("MANUALLY ADDING PAPERS TO DATABASE")
    print("="*60)
    print(f"Database: {db_path}")
    print(f"Papers to add: {len(dois)}")
    print("="*60 + "\n")
    
    # Initialize database
    db = PaperDatabase(db_path=db_path)
    
    # Create a query record for these manually added papers
    query_text = f"Manual addition of {len(dois)} papers"
    query_id = db.insert_query(query_text, QUERY_DESCRIPTION)
    print(f"Created query record with ID: {query_id}\n")
    
    # Track statistics
    added = 0
    skipped = 0
    errors = 0
    
    # Process each paper
    for doi, paper_data in dois.items():
        try:
            # Check if paper already exists
            existing = db.get_paper_by_doi(doi)
            if existing:
                print(f"⏭  Skipped (already exists): {doi}")
                skipped += 1
                continue
            
            # Create PaperMetadata object
            # Note: We don't have PMID, so we'll use DOI as identifier
            metadata = PaperMetadata(
                pmid=f"MANUAL_{doi.replace('/', '_')}",  # Create a unique ID
                doi=doi,
                title=paper_data.get("name"),
                abstract=paper_data.get("abstrat"),  # Note: typo in source data
                collection_date=datetime.now().isoformat(),
                query_id=query_id,
                source="Manual",
                is_full_text_pmc=False,
                openalex_retrieved=False
            )
            
            # Insert into database
            if db.insert_paper(metadata):
                print(f"✓ Added: {paper_data.get('name')[:60]}...")
                added += 1
            else:
                print(f"✗ Failed to add: {doi}")
                errors += 1
                
        except Exception as e:
            print(f"✗ Error processing {doi}: {e}")
            errors += 1
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total papers in source: {len(dois)}")
    print(f"Successfully added: {added}")
    print(f"Skipped (already exist): {skipped}")
    print(f"Errors: {errors}")
    print("="*60)
    
    # Export updated database
    if added > 0:
        print("\nExporting updated database to JSON...")
        json_path = db.export_to_json(compact=True)
        print(f"✓ Exported to: {json_path}")
    
    db.close()
    print("\nDone!")

if __name__ == "__main__":
    main()
