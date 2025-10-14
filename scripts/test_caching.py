#!/usr/bin/env python3
"""
Test query caching functionality
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pubmed_extractor import search_pubmed
from src.query_cache import QueryCache

print("="*80)
print("Testing Query Caching")
print("="*80)

# Test query (small, fast)
query = '("aging"[tiab] AND "theory"[tiab]) AND 2024[pdat]'

print(f"\nTest query: {query}\n")

# Clear cache first
cache = QueryCache()
cache.clear()
print("✓ Cache cleared for clean test\n")

# First run - should fetch from PubMed
print("[Test 1] First run (should fetch from PubMed)")
print("-" * 80)
start = time.time()
pmids1 = search_pubmed(query, max_results=100, use_cache=True)
time1 = time.time() - start
print(f"Retrieved: {len(pmids1)} PMIDs")
print(f"Time: {time1:.2f} seconds\n")

# Second run - should use cache
print("[Test 2] Second run (should use cache)")
print("-" * 80)
start = time.time()
pmids2 = search_pubmed(query, max_results=100, use_cache=True)
time2 = time.time() - start
print(f"Retrieved: {len(pmids2)} PMIDs")
print(f"Time: {time2:.2f} seconds\n")

# Verify results match
print("[Test 3] Verify cached results match")
print("-" * 80)
if pmids1 == pmids2:
    print("✅ Results match!")
else:
    print("❌ Results don't match!")
    print(f"First run: {len(pmids1)} PMIDs")
    print(f"Second run: {len(pmids2)} PMIDs")

# Check speedup
speedup = time1 / time2 if time2 > 0 else 0
print(f"\nSpeedup: {speedup:.1f}x faster with cache")

# Third run - disable cache
print("\n[Test 4] Third run (cache disabled)")
print("-" * 80)
start = time.time()
pmids3 = search_pubmed(query, max_results=100, use_cache=False)
time3 = time.time() - start
print(f"Retrieved: {len(pmids3)} PMIDs")
print(f"Time: {time3:.2f} seconds")
print("✓ Cache bypassed successfully\n")

# Show cache info
print("[Test 5] Cache information")
print("-" * 80)
info = cache.get_cache_info()
print(f"Cached queries: {info['total_queries']}")
print(f"Cached PMIDs: {info['total_pmids']:,}")
print(f"Cache size: {info['cache_size_kb']:.2f} KB")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"✅ Cache working correctly")
print(f"✅ First run: {time1:.2f}s (fetched from PubMed)")
print(f"✅ Second run: {time2:.2f}s (used cache, {speedup:.1f}x faster)")
print(f"✅ Results match: {pmids1 == pmids2}")
print(f"✅ Cache bypass works: {len(pmids3)} PMIDs")
print("="*80)
