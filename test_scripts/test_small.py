#!/usr/bin/env python3
"""
Small test example - collects just 10 papers for testing
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import collect_papers

# Simple query that will return results quickly
query = """
( "Theory of Aging" ) AND ( 2024:2025[pdat] )
"""

# Collect only 10 papers for testing
print("Starting small test collection (10 papers)...")
collect_papers(
    query=query,
    max_results=10,
    use_threading=False,
    query_description="Test query: Theory of Aging papers from 2024-2025"
)

print("\n" + "="*60)
print("Test completed! Check the results:")
print("  - Database: ./paper_collection/data/papers.db")
print("  - JSON export: ./paper_collection/data/papers_export.json")
print("="*60)
