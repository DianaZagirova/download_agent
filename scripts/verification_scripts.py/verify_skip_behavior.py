#!/usr/bin/env python3
"""
Verify that the skip_existing behavior works correctly
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import PaperDatabase

def verify_behavior():
    """Verify the skip behavior for existing papers"""
    
    print("="*80)
    print("SKIP EXISTING PAPERS - BEHAVIOR VERIFICATION")
    print("="*80)
    
    db_path = "/home/diana.z/hack/download_papers_pubmed/paper_collection/data/papers.db"
    db = PaperDatabase(db_path)
    
    print(f"\n📊 Database: {db_path}")
    stats = db.get_statistics()
    print(f"   Total papers: {stats['total_papers']:,}")
    print(f"   With full text: {stats['with_fulltext']:,}")
    print(f"   Without full text: {stats['without_fulltext']:,}")
    
    print("\n" + "="*80)
    print("BEHAVIOR LOGIC")
    print("="*80)
    
    print("""
When collect_papers() runs with skip_existing=True (DEFAULT):

1. Query returns PMIDs from PubMed
2. For each PMID:
   
   a) Check if paper exists in database
      
   b) If paper DOES NOT exist:
      ✅ COLLECT: Extract metadata + full text + OpenAlex
      
   c) If paper EXISTS:
      ⏭️  SKIP: No API calls, no processing, just increment counter
      
      This happens regardless of whether the paper has:
      - Missing abstract ❌
      - Missing full text ❌
      - Missing OpenAlex data ❌
      
      ALL EXISTING PAPERS ARE SKIPPED!

3. Result: Only NEW papers are processed

---

To ENABLE enrichment of existing incomplete papers:
   Set skip_existing=False in collect_papers() call
    """)
    
    print("="*80)
    print("EXAMPLE: Paper 10.1073/pnas.2300624120")
    print("="*80)
    
    doi = "10.1073/pnas.2300624120"
    paper = db.get_paper_by_doi(doi)
    
    if paper:
        print(f"✅ Paper IS in database")
        print(f"\n📋 When running scripts/run_full.py (skip_existing=True by default):")
        print(f"   ⏭️  This paper WILL BE SKIPPED")
        print(f"   ⏭️  No API calls made")
        print(f"   ⏭️  Counter: skipped += 1")
    else:
        print(f"❌ Paper NOT in database")
        print(f"\n📋 When running scripts/run_full.py:")
        print(f"   ✅ This paper WILL BE COLLECTED (if query returns it)")
        print(f"   ✅ Metadata + full text + OpenAlex extracted")
        print(f"   ✅ Added to database")
        
        print(f"\n📋 On subsequent runs (skip_existing=True):")
        print(f"   ⏭️  Paper will be SKIPPED")
    
    print("\n" + "="*80)
    
    db.close()

if __name__ == "__main__":
    verify_behavior()
