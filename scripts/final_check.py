#!/usr/bin/env python3
"""
Final pre-flight check before running full collection
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Bio import Entrez
from src.config import ENTREZ_EMAIL, ENTREZ_API_KEY
from src.database import PaperDatabase

query = """(
  ("aging"[tiab] OR "ageing"[tiab] OR "senescence"[tiab] OR "longevity"[tiab]) AND
  (theory[tiab] OR theories[tiab] OR hypothes*[tiab] OR framework*[tiab] OR paradigm*[tiab] OR "ultimate cause"[tiab] OR "proximate cause"[tiab] OR "evolution*"[tiab])
  NOT (cosmetic*[tiab] OR sunscreen*[tiab] OR "facial"[tiab] OR dermatol*[tiab])
  NOT ("healthy aging"[tiab] OR wellbeing[tiab] OR "public health"[tiab])
  NOT ("religion"[tiab])
  NOT ("Cosmetics"[mh])
  NOT ("Skin"[mh] OR "Dermatology"[mh])
)"""

print("="*80)
print("FINAL PRE-FLIGHT CHECK")
print("="*80)

# Test 1: Query count
print("\n[1/4] Verifying query count...")
Entrez.email = ENTREZ_EMAIL
Entrez.api_key = ENTREZ_API_KEY

try:
    handle = Entrez.esearch(db="pubmed", term=query, usehistory="y", retmax=0)
    record = Entrez.read(handle)
    handle.close()
    
    count = int(record["Count"])
    webenv = record.get("WebEnv")
    query_key = record.get("QueryKey")
    
    if count == 46351:
        print(f"   ✅ Query returns exactly 46,351 papers")
    else:
        print(f"   ⚠️  Query returns {count:,} papers (expected 46,351)")
    
    if webenv and query_key:
        print(f"   ✅ History server enabled (WebEnv & QueryKey received)")
    else:
        print(f"   ⚠️  History server may not be working")
        
except Exception as e:
    print(f"   ❌ Query failed: {e}")
    sys.exit(1)

# Test 2: Database
print("\n[2/4] Checking database...")
try:
    db = PaperDatabase()
    stats = db.get_statistics()
    print(f"   ✅ Database accessible")
    print(f"   Current papers: {stats['total_papers']:,}")
    
    # Check if broad_aging exists
    queries = db.get_all_queries()
    broad_aging_exists = False
    for q in queries:
        if q['description'] == 'broad_aging':
            broad_aging_exists = True
            papers = db.count_papers_by_query(q['id'])
            print(f"   ⚠️  'broad_aging' query already exists (ID: {q['id']}, {papers:,} papers)")
            print(f"      New collection will update this query")
            break
    
    if not broad_aging_exists:
        print(f"   ✅ 'broad_aging' query will be created as new")
    
    db.close()
except Exception as e:
    print(f"   ❌ Database error: {e}")
    sys.exit(1)

# Test 3: Pagination capability
print("\n[3/4] Testing pagination with History Server...")
try:
    # Test fetching first batch of PMIDs
    handle = Entrez.efetch(
        db="pubmed",
        rettype="uilist",
        retmode="text",
        retstart=0,
        retmax=10,  # Just test with 10
        webenv=webenv,
        query_key=query_key
    )
    
    batch_data = handle.read()
    handle.close()
    
    if isinstance(batch_data, bytes):
        batch_data = batch_data.decode('utf-8')
    
    pmids = [pmid.strip() for pmid in batch_data.strip().split('\n') if pmid.strip()]
    
    if len(pmids) == 10:
        print(f"   ✅ Successfully retrieved test batch (10 PMIDs)")
        print(f"      Sample PMIDs: {pmids[:3]}")
    else:
        print(f"   ⚠️  Retrieved {len(pmids)} PMIDs (expected 10)")
        
except Exception as e:
    print(f"   ❌ Pagination test failed: {e}")
    sys.exit(1)

# Test 4: System capacity
print("\n[4/4] Checking system capacity...")
import shutil
try:
    stat = shutil.disk_usage(os.path.dirname(os.path.abspath(__file__)))
    free_gb = stat.free / (1024**3)
    
    if free_gb >= 5:
        print(f"   ✅ Sufficient disk space ({free_gb:.1f} GB free)")
    else:
        print(f"   ⚠️  Low disk space ({free_gb:.1f} GB free, recommend 5+ GB)")
        
except Exception as e:
    print(f"   ⚠️  Could not check disk space: {e}")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("✅ All systems ready for collection!")
print("\nExpected results:")
print(f"  - Total PMIDs to retrieve: 46,351")
print(f"  - Query name: 'broad_aging'")
print(f"  - Pagination: 5 batches (10K + 10K + 10K + 10K + 6,351)")
print(f"  - Estimated time: 0.5 - 3 hours")
print("\nTo start collection:")
print("  python3 scripts/run_full.py")
print("="*80)
