#!/usr/bin/env python3
"""
Test script to verify if the alternative implementation can retrieve the full text
for the paper with DOI 10.1016/j.arr.2016.06.005
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Bio import Entrez
import threading
import time
import xml.etree.ElementTree as ET

# Configuration constants
MAX_REQUESTS_PER_SEC = 9
semaphore = threading.BoundedSemaphore(value=MAX_REQUESTS_PER_SEC)
last_req_time = [0]  # List to allow modification in nested scopes

# Set up Entrez
Entrez.email = "diana.z@insilicomedicine.com"
Entrez.api_key = "9f5d0d5238d7eb65e0526c84d79a5b945d08"

# Test DOI
test_doi = "10.1016/j.arr.2016.06.005"

def safe_ncbi_call(func, *args, **kwargs):
    """
    Wrapper for Entrez API calls with timeout handling, retries, and rate-limiting.
    """
    tries = 3
    for attempt in range(tries):
        try:
            with semaphore:
                # Respect NCBI rate limit: ensure minimum time between requests
                elapsed = time.time() - last_req_time[0]
                wait = max(0, 1.0/MAX_REQUESTS_PER_SEC - elapsed)
                if wait:
                    time.sleep(wait)
                last_req_time[0] = time.time()
                return func(*args, **kwargs)
        except Exception as e:
            if attempt < tries-1:
                print(f"Retrying {func.__name__} for args {args} (Error: {str(e)})")
                time.sleep(2)
            else:
                print(f"Failed {func.__name__} for args {args}, skipping (Error: {str(e)})")
                return None

def collect_pmc_doc(pmcid):
    """
    Retrieve and parse a full-text article from PubMed Central.
    """
    # Normalize PMCID format (strip 'PMC' prefix if present)
    pmcid_stripped = pmcid.replace("PMC", "") if pmcid.startswith("PMC") else pmcid
    
    # Initialize result structure
    meta = {'metadata': {}, 'page_content': ''}
    
    # Fetch the document from PMC
    handle = safe_ncbi_call(Entrez.efetch, db="pmc", id=pmcid_stripped, rettype="full", retmode="xml")
    if handle is None:
        return None
        
    # Parse the XML content
    try:
        records = handle.read()
        handle.close()
        if isinstance(records, bytes):
            records = records.decode("utf-8")
        root = ET.fromstring(records)
    except Exception as e:
        print(f"Failed to parse XML for PMCID {pmcid}: {str(e)}")
        return None

    # Prefer <article> as root
    article_tag = root.find('.//article') or (root if root.tag == 'article' else None)
    if not article_tag and root.find('.//pmc-articleset') is not None:
        article_tag = root.find('.//pmc-articleset/article')
    if not article_tag:
        print(f"No <article> tag found in XML for PMCID {pmcid}!")
        return None

    # Article attributes
    meta['metadata']['Article Type'] = article_tag.attrib.get('article-type', 'Not specified')
    doi = article_tag.find('.//article-id[@pub-id-type="doi"]')
    meta['metadata']['DOI'] = doi.text if doi is not None else "DOI not available"

    pmid = article_tag.find('.//article-id[@pub-id-type="pmid"]')
    meta['metadata']['PubMed Link'] = f"https://pubmed.ncbi.nlm.nih.gov/{pmid.text}/" if pmid is not None else "Not available"
    meta['metadata']['PMC Link'] = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid_stripped}/"
    journal_name = article_tag.find('.//journal-title')
    if journal_name is not None:
        meta['metadata']['Journal'] = journal_name.text
    title = article_tag.find('.//article-title')
    if title is not None:
        meta['metadata']['Title'] = ''.join(title.itertext())
    pub_year = article_tag.find('.//pub-date/year')
    if pub_year is not None:
        meta['metadata']['Year Published'] = pub_year.text

    # Abstract
    abstract = article_tag.find('.//abstract')
    if abstract is not None:
        abstract_text = ' '.join(abstract.itertext())
        meta['page_content'] += f"ABSTRACT:\n{abstract_text}\n\n"

    # Full text
    def extract_all_sections(parent, lvl=1):
        text = ''
        sect_title = parent.find('./title')
        if sect_title is not None:
            text += f"{' #'*lvl} {''.join(sect_title.itertext()).strip()}\n"
        for p in parent.findall('./p'):
            text += ''.join(p.itertext()).strip() + '\n\n'
        for s in parent.findall('./sec'):
            text += extract_all_sections(s, lvl=lvl+1)
        return text

    body = article_tag.find('.//body')
    if body is not None:
        for top_sec in body.findall('./sec'):
            meta['page_content'] += extract_all_sections(top_sec, lvl=1)
        for p in body.findall('./p'):
            meta['page_content'] += ''.join(p.itertext()).strip() + '\n\n'

    # Tables
    tables = article_tag.findall('.//table-wrap')
    if tables:
        meta['page_content'] += "TABLES:\n"
        for table_idx, table in enumerate(tables, 1):
            caption = table.find('.//caption')
            if caption is not None:
                meta['page_content'] += f"Table {table_idx}: {' '.join(caption.itertext())}\n"
            table_content = table.find('.//table')
            if table_content is not None:
                meta['page_content'] += ' '.join(table_content.itertext()) + "\n\n"

    # Figures
    figures = article_tag.findall('.//fig')
    if figures:
        meta['page_content'] += "FIGURES:\n"
        for fig_idx, figure in enumerate(figures, 1):
            caption = figure.find('.//caption')
            if caption is not None:
                meta['page_content'] += f"Figure {fig_idx}: {' '.join(caption.itertext())}\n\n"

    # References
    refs = article_tag.findall('.//ref-list//ref')
    if refs:
        meta['page_content'] += "REFERENCES:\n"
        for ref_idx, ref in enumerate(refs, 1):
            ref_text = ' '.join(ref.itertext())
            meta['page_content'] += f"{ref_idx}. {ref_text}\n"
    
    return meta

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

# Fetch metadata for the PMID
print("\nFetching metadata for PMID...")
handle = safe_ncbi_call(Entrez.efetch, db="pubmed", id=pmid, retmode="xml")
if handle is None:
    print("Failed to fetch metadata.")
    sys.exit(1)

# Parse the returned XML
try:
    records = Entrez.read(handle)
    handle.close()
except Exception as e:
    print(f"Failed to process metadata: {str(e)}")
    sys.exit(1)

# Extract PMC IDs from article identifiers
article = records['PubmedArticle'][0]
pmcids = [str(id_item) for id_item in article['PubmedData']['ArticleIdList'] 
         if str(id_item).startswith('PMC')]

print(f"Found {len(pmcids)} PMC IDs: {', '.join(pmcids)}")

# Try to retrieve full text using each PMC ID
for pmcid in pmcids:
    print(f"\nAttempting to retrieve full text using PMCID: {pmcid}...")
    document = collect_pmc_doc(pmcid)
    
    if document:
        print(f"Successfully retrieved full text!")
        print(f"Title: {document['metadata'].get('Title', 'Unknown')}")
        print(f"Full text length: {len(document['page_content'])} characters")
        print("\nFirst 200 characters of full text:")
        print(document['page_content'][:200] + "...")
        
        # Save the full text to a file for inspection
        output_file = f"paper_{pmid}_fulltext.txt"
        with open(output_file, "w") as f:
            f.write(document['page_content'])
        print(f"\nFull text saved to {output_file}")
        
        break
    else:
        print(f"Failed to retrieve full text using {pmcid}.")
else:
    print("\nFailed to retrieve full text using any PMC ID.")

# If no PMC ID worked, try searching for the paper in PMC using the DOI directly
if not pmcids or document is None:
    print(f"\nAttempting to search for the paper in PMC using DOI...")
    handle = safe_ncbi_call(
        Entrez.esearch,
        db="pmc",
        term=f"{test_doi}[DOI]",
        retmax=1
    )
    
    if handle:
        record = Entrez.read(handle)
        handle.close()
        
        if record["IdList"]:
            pmcid = record["IdList"][0]
            print(f"Found PMC ID from DOI search: {pmcid}")
            
            print(f"Attempting to retrieve full text...")
            document = collect_pmc_doc(pmcid)
            
            if document:
                print(f"Successfully retrieved full text!")
                print(f"Title: {document['metadata'].get('Title', 'Unknown')}")
                print(f"Full text length: {len(document['page_content'])} characters")
                print("\nFirst 200 characters of full text:")
                print(document['page_content'][:200] + "...")
                
                # Save the full text to a file for inspection
                output_file = f"paper_{pmid}_fulltext_from_doi.txt"
                with open(output_file, "w") as f:
                    f.write(document['page_content'])
                print(f"\nFull text saved to {output_file}")
            else:
                print("Failed to retrieve full text using PMC ID from DOI search.")
        else:
            print("No PMC ID found from DOI search.")
    else:
        print("Failed to search PMC using DOI.")
