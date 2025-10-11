#!/usr/bin/env python3
"""
Test script to verify that previously failed PMIDs can now be extracted
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pubmed_extractor import extract_pubmed_metadata, extract_pubmed_metadata_batch

# The 5 PMIDs that failed in the previous run
FAILED_PMIDS = [
    "13458524",  # 1957 - "An hypothesis of psychological aging"
    "1801503",   # 1991 - "The glucocorticoid hypothesis of brain aging"
    "19947383",  # 2009 - Russian language paper
    "21204345",  # Could not retrieve metadata
    "3627350"    # 1987 - "Increased calcium-current hypothesis"
]

def test_individual_extraction():
    """Test individual extraction for each failed PMID"""
    print("="*60)
    print("TESTING INDIVIDUAL EXTRACTION")
    print("="*60)
    
    success_count = 0
    for pmid in FAILED_PMIDS:
        print(f"\nTesting PMID {pmid}...")
        metadata = extract_pubmed_metadata(pmid)
        
        if metadata:
            print(f"  ✓ SUCCESS")
            print(f"    Title: {metadata.title[:80] if metadata.title else 'N/A'}...")
            print(f"    Year: {metadata.year if metadata.year else 'N/A'}")
            print(f"    DOI: {metadata.doi if metadata.doi else 'N/A'}")
            print(f"    Journal: {metadata.journal[:50] if metadata.journal else 'N/A'}")
            success_count += 1
        else:
            print(f"  ✗ FAILED - Could not extract metadata")
    
    print(f"\n{'='*60}")
    print(f"Individual extraction: {success_count}/{len(FAILED_PMIDS)} successful")
    print(f"{'='*60}\n")
    return success_count


def test_batch_extraction():
    """Test batch extraction for all failed PMIDs"""
    print("="*60)
    print("TESTING BATCH EXTRACTION")
    print("="*60)
    
    print(f"\nExtracting batch of {len(FAILED_PMIDS)} PMIDs...")
    batch_results = extract_pubmed_metadata_batch(FAILED_PMIDS)
    
    print(f"\nBatch extraction returned {len(batch_results)} results")
    
    for pmid in FAILED_PMIDS:
        if pmid in batch_results:
            metadata = batch_results[pmid]
            print(f"\n✓ PMID {pmid}:")
            print(f"  Title: {metadata.title[:80] if metadata.title else 'N/A'}...")
            print(f"  Year: {metadata.year if metadata.year else 'N/A'}")
        else:
            print(f"\n✗ PMID {pmid}: NOT in batch results")
    
    print(f"\n{'='*60}")
    print(f"Batch extraction: {len(batch_results)}/{len(FAILED_PMIDS)} successful")
    print(f"{'='*60}\n")
    return len(batch_results)


def test_fallback_mechanism():
    """Test the new fallback mechanism in process_batch"""
    print("="*60)
    print("TESTING FALLBACK MECHANISM")
    print("="*60)
    
    print("\nSimulating process_batch behavior:")
    print("1. Try batch extraction")
    batch_results = extract_pubmed_metadata_batch(FAILED_PMIDS)
    print(f"   Batch returned: {len(batch_results)} results")
    
    print("\n2. Check for missing PMIDs")
    missing_pmids = [pmid for pmid in FAILED_PMIDS if pmid not in batch_results]
    print(f"   Missing: {len(missing_pmids)} PMIDs")
    
    if missing_pmids:
        print("\n3. Try individual extraction for missing PMIDs")
        recovered = 0
        for pmid in missing_pmids:
            print(f"   Trying PMID {pmid}...")
            metadata = extract_pubmed_metadata(pmid)
            if metadata:
                batch_results[pmid] = metadata
                recovered += 1
                print(f"     ✓ Recovered")
            else:
                print(f"     ✗ Still failed")
        
        print(f"\n   Recovered: {recovered}/{len(missing_pmids)}")
    
    print(f"\n{'='*60}")
    print(f"Final results: {len(batch_results)}/{len(FAILED_PMIDS)} successful")
    print(f"{'='*60}\n")
    return len(batch_results)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("FAILED PMID EXTRACTION TEST")
    print("="*60)
    print(f"\nTesting {len(FAILED_PMIDS)} PMIDs that failed in previous run\n")
    
    # Test 1: Individual extraction
    individual_success = test_individual_extraction()
    
    # Test 2: Batch extraction
    batch_success = test_batch_extraction()
    
    # Test 3: Fallback mechanism
    fallback_success = test_fallback_mechanism()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Individual extraction: {individual_success}/{len(FAILED_PMIDS)} successful")
    print(f"Batch extraction:      {batch_success}/{len(FAILED_PMIDS)} successful")
    print(f"With fallback:         {fallback_success}/{len(FAILED_PMIDS)} successful")
    print("="*60)
    
    if fallback_success == len(FAILED_PMIDS):
        print("\n✓ ALL PMIDS CAN NOW BE EXTRACTED!")
    elif fallback_success > batch_success:
        print(f"\n✓ Fallback mechanism recovered {fallback_success - batch_success} additional PMIDs")
    else:
        print(f"\n⚠ {len(FAILED_PMIDS) - fallback_success} PMIDs still cannot be extracted")
    
    print()
