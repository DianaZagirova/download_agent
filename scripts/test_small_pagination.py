#!/usr/bin/env python3
"""
Quick test of pagination with small result set
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pubmed_extractor import search_pubmed

# Small test query
query = '("aging"[tiab] AND "theory"[tiab]) AND 2024[pdat]'

print("Testing pagination with small query...")
pmid_list = search_pubmed(query, max_results=100)

print(f"\n✅ Retrieved {len(pmid_list)} PMIDs")
print(f"Sample: {pmid_list[:5]}")
