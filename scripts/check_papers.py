#!/usr/bin/env python3
"""
Quick script to check if specific papers exist in the database
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import PaperDatabase

# DOIs to check
dois_to_check = [
    '10.1073/pnas.2300624120',
    '10.1152/physrev.00047.2006',
    '10.3390/vaccines12121314'
]

# Database paths to check
db_paths = [
    '/home/diana.z/hack/download_papers_pubmed/paper_collection/data/papers.db',
    '/home/diana.z/hack/download_papers_pubmed/aging_theories_collection/data/papers.db'
]

print("=" * 80)
print("CHECKING FOR PAPERS IN DATABASES")
print("=" * 80)

for db_path in db_paths:
    if not os.path.exists(db_path):
        print(f"\n❌ Database not found: {db_path}")
        continue
    
    print(f"\n📊 Checking database: {db_path}")
    print("-" * 80)
    
    try:
        db = PaperDatabase(db_path)
        
        for doi in dois_to_check:
            exists = db.paper_exists_by_doi(doi)
            
            if exists:
                # Get paper details
                paper = db.get_paper_by_doi(doi)
                print(f"\n✅ FOUND: {doi}")
                print(f"   PMID: {paper.pmid}")
                print(f"   Title: {paper.title[:100]}...")
                print(f"   Year: {paper.year}")
                print(f"   Journal: {paper.journal}")
                print(f"   Has Full Text: {'Yes' if paper.is_full_text_pmc else 'No'}")
                print(f"   Has Abstract: {'Yes' if paper.abstract else 'No'}")
            else:
                print(f"\n❌ NOT FOUND: {doi}")
        
        db.close()
        
    except Exception as e:
        print(f"   Error accessing database: {str(e)}")

print("\n" + "=" * 80)
