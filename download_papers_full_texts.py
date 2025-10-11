#!/usr/bin/env python3
"""
PMC Full Text Downloader
"""
import os
import time
import pickle
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from Bio import Entrez
import xml.etree.ElementTree as ET
from tqdm import tqdm
from src.text_cleaner import clean_text_comprehensive

# Configuration constants
SAVE_DIR = './paper_full_texts'
os.makedirs(SAVE_DIR, exist_ok=True)

# NCBI API rate limiting (max 10 requests/sec, we use 9 to be safe)
MAX_REQUESTS_PER_SEC = 8
semaphore = threading.BoundedSemaphore(value=MAX_REQUESTS_PER_SEC)
last_req_time = [0]  # List to allow modification in nested scopes

def safe_ncbi_call(func, *args, **kwargs):
    """
    Wrapper for Entrez API calls with timeout handling, retries, and rate-limiting.
    
    Args:
        func: The Entrez function to call
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        The result of the function call or None if all attempts failed
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
    
    Args:
        pmcid: The PubMed Central ID (with or without 'PMC' prefix)
        
    Returns:
        Dictionary containing metadata and full text content, or None if retrieval failed
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
        raise ValueError("No <article> tag found in XML!")

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
    
    # Clean the full text before returning
    meta['page_content'] = clean_text_comprehensive(meta['page_content'], remove_references=True)
    
    return meta

def fetch_pmcids_batch(pmid_batch):
    """
    Process a batch of PubMed IDs to retrieve their corresponding PMC articles.
    
    Args:
        pmid_batch: List of PubMed IDs to process
        
    Returns:
        Tuple of (failed_pmids, multiple_pmcids_map, retrieved_documents)
    """
    failed_pmids = []
    multiple_pmcids_map = {}
    retrieved_documents = {}
    
    # Convert batch to comma-separated string for API call
    joined_ids = ','.join(map(str, pmid_batch))
    
    # Fetch metadata for all PMIDs in batch
    handle = safe_ncbi_call(Entrez.efetch, db="pubmed", id=joined_ids, retmode="xml")
    if handle is None:
        failed_pmids.extend(pmid_batch)
        return failed_pmids, multiple_pmcids_map, retrieved_documents

    # Parse the returned XML
    try:
        records = Entrez.read(handle)
        handle.close()
    except Exception as e:
        failed_pmids.extend(pmid_batch)
        print(f"Failed to process batch {pmid_batch}: {str(e)}")
        return failed_pmids, multiple_pmcids_map, retrieved_documents

    # Process each article in the batch
    articles = records['PubmedArticle']
    for article in articles:
        try:
            pmid = str(article['MedlineCitation']['PMID'])
            # Extract PMC IDs from article identifiers
            pmcids = [str(id_item) for id_item in article['PubmedData']['ArticleIdList'] 
                     if str(id_item).startswith('PMC')]
                     
            if pmcids:
                # Track articles with multiple PMC IDs
                if len(pmcids) > 1:
                    multiple_pmcids_map[pmid] = pmcids
                    
                # Retrieve full text using the first PMC ID
                document = collect_pmc_doc(pmcids[0])
                if document:
                    document['metadata']['PMCID'] = pmcids[0]
                    retrieved_documents[pmid] = document
                else:
                    failed_pmids.append(pmid)
            else:
                # No PMC ID available
                failed_pmids.append(pmid)
        except Exception as e:
            failed_pmids.append(article['MedlineCitation']['PMID'])
            print(f"Error processing article {article['MedlineCitation']['PMID']}: {str(e)}")
            
    return failed_pmids, multiple_pmcids_map, retrieved_documents

def main():

    Entrez.email = "diana.z@insilicomedicine.com"
    Entrez.api_key = "9f5d0d5238d7eb65e0526c84d79a5b945d08"
    
    search_query = (
        '(("novel"[Title] OR "new"[Title] OR "promising"[Title] OR "candidate"[Title] OR "emerging"[Title]) AND '
        '("target"[Title] OR "targets"[Title])) NOT "review"[Publication Type] '
        'NOT "editorial"[Publication Type] NOT "case reports"[Publication Type]) '
        'AND (2005:2026[pdat]) AND (ffrft[Filter])'
    )

    # Search parameters
    max_results = 50000
    database = "pubmed"
    
    print(f"Searching PubMed for articles matching query...")
    handle = safe_ncbi_call(
        Entrez.esearch,
        db=database,
        term=search_query,
        retmax=max_results,
        sort="relevance"
    )
    
    if not handle:
        print("Initial search failed. Please check your connection and try again.")
        return
        
    record = Entrez.read(handle)
    handle.close()

    id_list = record["IdList"]    
    print(f"Found {len(id_list)} papers with full text filter matching the query")

    failed_pmids = []
    multiple_pmcids = {}
    retrieved_documents = {}
    
    batch_size = 20  
    num_threads = 2  
    checkpoint_every = 32 
    
    start_time = time.time()
    print(f"Starting download with {num_threads} threads, batch size {batch_size}...")

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        batches = [id_list[i:i+batch_size] for i in range(0, len(id_list), batch_size)]
        futures = {executor.submit(fetch_pmcids_batch, batch): batch for batch in batches}
        
        for i, future in enumerate(tqdm(as_completed(futures), total=len(futures), desc="Processing batches")):
            try:
                batch_failed, batch_multiple, batch_documents = future.result()
                failed_pmids.extend(batch_failed)
                multiple_pmcids.update(batch_multiple)
                retrieved_documents.update(batch_documents)
            except Exception as exc:
                print(f"Batch failed with exception: {exc}")

            if i == 0 or (i + 1) % checkpoint_every == 0 or (i + 1) == len(futures):
                checkpoint_path = os.path.join(SAVE_DIR, f'checkpoint_{i}')
                with open(os.path.join(SAVE_DIR, f'documents_checkpoint_{i}.pkl'), 'wb') as f:
                    pickle.dump(retrieved_documents, f)
                with open(os.path.join(SAVE_DIR, f'failed_pmids_checkpoint_{i}.pkl'), 'wb') as f:
                    pickle.dump(failed_pmids, f)
                with open(os.path.join(SAVE_DIR, f'multiple_pmcids_checkpoint_{i}.pkl'), 'wb') as f:
                    pickle.dump(multiple_pmcids, f)
                print(f'[Checkpoint] Saved progress at {i+1}/{len(futures)} batches ({len(retrieved_documents)} papers processed).')
                
    elapsed = time.time() - start_time
    print(f"\nDownload completed in {elapsed:.2f} seconds ({elapsed/60:.2f} minutes).")
    print(f"Total papers successfully retrieved: {len(retrieved_documents)}")
    print(f"Total papers that failed: {len(failed_pmids)}")
    print(f"Papers with multiple PMC IDs: {len(multiple_pmcids)}")

    print("\nSaving final results...")
    with open(os.path.join(SAVE_DIR, 'documents_final.pkl'), 'wb') as f:
        pickle.dump(retrieved_documents, f)
    with open(os.path.join(SAVE_DIR, 'failed_pmids_final.pkl'), 'wb') as f:
        pickle.dump(failed_pmids, f)
    with open(os.path.join(SAVE_DIR, 'multiple_pmcids_final.pkl'), 'wb') as f:
        pickle.dump(multiple_pmcids, f)
    print('Final results saved successfully.')

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
    except Exception as e:
        print(f"\nError in main execution: {str(e)}")
