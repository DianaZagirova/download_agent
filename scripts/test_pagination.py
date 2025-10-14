#!/usr/bin/env python3
"""
Test pagination functionality for large PubMed queries
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pubmed_extractor import search_pubmed

# Test query
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
print("Testing Pagination with broad_aging Query")
print("="*80)
print(f"Expected count: 46,351 papers\n")

# Test retrieval
pmid_list = search_pubmed(query, max_results=50000)

print("\n" + "="*80)
print("RESULTS")
print("="*80)
print(f"Total PMIDs retrieved: {len(pmid_list):,}")
print(f"Expected: 46,351")

if len(pmid_list) == 46351:
    print("✅ SUCCESS: Retrieved all expected PMIDs")
elif len(pmid_list) > 46000:
    print(f"✅ CLOSE: Retrieved {len(pmid_list):,} PMIDs (within acceptable range)")
else:
    print(f"⚠️  WARNING: Retrieved {len(pmid_list):,} PMIDs, expected 46,351")

# Check for duplicates
unique_pmids = set(pmid_list)
if len(unique_pmids) == len(pmid_list):
    print(f"✅ No duplicate PMIDs")
else:
    print(f"⚠️  Found {len(pmid_list) - len(unique_pmids)} duplicate PMIDs")

# Sample some PMIDs
print(f"\nSample PMIDs (first 10):")
for i, pmid in enumerate(pmid_list[:10], 1):
    print(f"  {i}. {pmid}")

print("\n" + "="*80)
print("Pagination test complete!")
print("="*80)
