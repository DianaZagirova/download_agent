#!/usr/bin/env python3
"""
Test script to verify fix for DOI and PMC ID identification
Tests with paper DOI: 10.1016/j.arr.2016.06.005

This script will print detailed information about article IDs and attempt to retrieve full text
using all available PMC IDs.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Bio import Entrez
from src.pubmed_extractor import safe_ncbi_call, extract_pubmed_metadata, extract_pmc_fulltext, process_paper
from src.config import ENTREZ_EMAIL, ENTREZ_API_KEY

# Set up Entrez
Entrez.email = ENTREZ_EMAIL
Entrez.api_key = ENTREZ_API_KEY

# Test DOI
test_doi = "10.1016/j.arr.2016.06.005"

print(f"Testing paper with DOI: {test_doi}")
print("-" * 70)

# First, search for the PMID using the DOI
print("Searching for PMID using DOI...")
handle = safe_ncbi_call(
    Entrez.esearch,
    db="pubmed",
    term=f"{test_doi}[DOI]",
    retmax=1
)

if not handle:
    print("Search failed.")
    sys.exit(1)

record = Entrez.read(handle)
handle.close()

if not record["IdList"]:
    print(f"No PMID found for DOI {test_doi}")
    sys.exit(1)

pmid = record["IdList"][0]
print(f"Found PMID: {pmid}")

# Now test the fixed metadata extraction
print("\nTesting metadata extraction with fixed code...")
metadata = extract_pubmed_metadata(pmid)

if metadata:
    print(f"Title: {metadata.title}")
    print(f"DOI: {metadata.doi}")
    print(f"PMCID: {metadata.pmcid}")
    print(f"Has full text in PMC: {metadata.is_full_text_pmc}")
    
    # Get all article IDs directly from PubMed
    print("\nFetching all article IDs directly from PubMed...")
    handle = safe_ncbi_call(Entrez.efetch, db="pubmed", id=pmid, retmode="xml")
    if handle is not None:
        try:
            records = Entrez.read(handle)
            handle.close()
            if records['PubmedArticle']:
                article = records['PubmedArticle'][0]
                article_ids = article['PubmedData'].get('ArticleIdList', [])
                print(f"Found {len(article_ids)} article IDs:")
                for id_item in article_ids:
                    id_type = id_item.attributes.get('IdType', 'unknown')
                    id_value = str(id_item)
                    print(f"  - {id_type}: {id_value}")
                
                # Try to extract PMC IDs
                pmcids = [str(id_item) for id_item in article_ids if str(id_item).startswith('PMC')]
                print(f"\nFound {len(pmcids)} PMC IDs: {', '.join(pmcids)}")
                
                # Try each PMC ID
                for pmcid in pmcids:
                    print(f"\nAttempting to extract full text using PMCID: {pmcid}...")
                    full_text, sections = extract_pmc_fulltext(pmcid)
                    if full_text:
                        print(f"Full text extracted successfully! ({len(full_text)} characters)")
                        print(f"Number of sections: {len(sections) if sections else 0}")
                        print("\nFirst 200 characters of full text:")
                        print(full_text[:200] + "...")
                        break
                    else:
                        print(f"Failed to extract full text using {pmcid}.")
        except Exception as e:
            print(f"Error getting article IDs: {str(e)}")
    else:
        print("Failed to fetch article data.")
else:
    print("Failed to extract metadata.")

# Test the complete process_paper function
print("\n" + "=" * 70)
print("Testing complete paper processing...")
print("=" * 70)

complete_metadata = process_paper(pmid)
if complete_metadata:
    print(f"Title: {complete_metadata.title}")
    print(f"DOI: {complete_metadata.doi}")
    print(f"PMCID: {complete_metadata.pmcid}")
    print(f"Has full text: {complete_metadata.has_full_text()}")
    print(f"Full text length: {len(complete_metadata.full_text) if complete_metadata.full_text else 0} characters")
    print(f"Number of sections: {len(complete_metadata.full_text_sections)}")
    
    if complete_metadata.has_full_text():
        print("\nTest SUCCESSFUL! Full text was retrieved.")
        print("\nFirst 200 characters of full text:")
        print(complete_metadata.full_text[:200] + "...")
    else:
        print("\nTest FAILED! Full text was not retrieved.")
        
        # Let's try to get the full text using the DOI directly
        print("\nAttempting to retrieve full text using DOI directly...")
        # This would require additional implementation
        print(f"DOI: {complete_metadata.doi}")
        print("Note: DOI-based full text retrieval is not implemented yet.")
else:
    print("Failed to process paper completely.")
