#!/usr/bin/env python3
"""
Test date-splitting functionality for large queries
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pubmed_extractor import search_pubmed

print("="*80)
print("Testing Date-Splitting Approach")
print("="*80)

# Test with a moderately large query (should trigger date splitting)
query = '("aging"[tiab] OR "ageing"[tiab]) AND (theory[tiab] OR hypothesis[tiab])'

print(f"\nQuery: {query}")
print("This should trigger date-splitting if >10K results...\n")

pmids = search_pubmed(query, max_results=15000)

print("\n" + "="*80)
print("RESULTS")
print("="*80)
print(f"Total PMIDs retrieved: {len(pmids):,}")
print(f"Unique PMIDs: {len(set(pmids)):,}")
print(f"Duplicates: {len(pmids) - len(set(pmids))}")

if len(pmids) > 10000:
    print("✅ Successfully retrieved >10K results using date splitting!")
else:
    print(f"✅ Retrieved {len(pmids):,} results")

print("\nSample PMIDs (first 10):")
for i, pmid in enumerate(pmids[:10], 1):
    print(f"  {i}. {pmid}")

print("\n" + "="*80)
print("Date splitting test complete!")
print("="*80)
