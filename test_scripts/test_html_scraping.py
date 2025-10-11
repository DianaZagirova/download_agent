#!/usr/bin/env python3
"""
Test HTML scraping fallback for papers with only abstract in XML
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pubmed_extractor import extract_pmc_fulltext

# Test PMCIDs
# These should trigger HTML scraping if XML only has abstract
test_pmcids = [
    "PMC5991498",  # A synopsis on aging
    "PMC9915297",  # Ageing and Keeping Pace with Technology
]

print("="*70)
print("TESTING HTML SCRAPING FALLBACK")
print("="*70)

for pmcid in test_pmcids:
    print(f"\n{'='*70}")
    print(f"Testing PMCID: {pmcid}")
    print("="*70)
    
    full_text, sections = extract_pmc_fulltext(pmcid)
    
    if full_text:
        print(f"\n✓ SUCCESS!")
        print(f"  Full text length: {len(full_text)} characters")
        print(f"  Sections found: {list(sections.keys())}")
        print(f"\n  First 200 chars of full_text:")
        print(f"  {'-'*70}")
        print(f"  {full_text[:200]}...")
        print(f"  {'-'*70}")
        
        # Check if it's more than just abstract
        if len(full_text) > 2000:
            print(f"\n  ✓ Has substantial content (> 2000 chars)")
        else:
            print(f"\n  ⚠ WARNING: Only {len(full_text)} chars - might be abstract only")
            
    else:
        print(f"\n✗ FAILED - No full text retrieved")
        print(f"  This paper might not have full text available in PMC")

print(f"\n{'='*70}")
print("TEST COMPLETED")
print("="*70)
