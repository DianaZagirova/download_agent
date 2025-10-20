#!/usr/bin/env python3
"""
PubMed metadata and full-text extractor
"""
import time
import threading
import re
import requests
from typing import Optional, List, Tuple, Dict
from Bio import Entrez
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

from .models import PaperMetadata
from .text_cleaner import clean_text_comprehensive, clean_abstract
from .config import (
    ENTREZ_EMAIL, ENTREZ_API_KEY, MAX_REQUESTS_PER_SEC,
    MAX_RETRIES, RETRY_DELAY, METADATA_FETCH_BATCH_SIZE
)


# Rate limiting setup
semaphore = threading.BoundedSemaphore(value=MAX_REQUESTS_PER_SEC)
last_req_time = [0]

EXTRACT_FIGURES = False
EXTRACT_TABLES = False

def safe_ncbi_call(func, *args, **kwargs):
    """
    Wrapper for Entrez API calls with timeout handling, retries, and rate-limiting.
    Includes exponential backoff and credential rotation for 429 (rate limit) errors.
    """
    from .config import rotate_credentials
    
    for attempt in range(MAX_RETRIES):
        try:
            with semaphore:
                # Respect NCBI rate limit
                elapsed = time.time() - last_req_time[0]
                wait = max(0, 1.0/MAX_REQUESTS_PER_SEC - elapsed)
                if wait:
                    time.sleep(wait)
                last_req_time[0] = time.time()
                return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e)
            
            # Check if it's a 429 rate limit error
            if '429' in error_str or 'Too Many Requests' in error_str:
                # Rotate to next set of credentials
                print(f"Rate limit hit (429). Rotating credentials...")
                new_creds = rotate_credentials()
                Entrez.email = new_creds['email']
                Entrez.api_key = new_creds['api_key']
                
                # Exponential backoff
                backoff_time = RETRY_DELAY * (2 ** attempt)  # 2s, 4s, 8s
                print(f"Backing off for {backoff_time}s (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(backoff_time)
            elif attempt < MAX_RETRIES - 1:
                print(f"Retrying {func.__name__} (attempt {attempt + 1}/{MAX_RETRIES}): {error_str}")
                time.sleep(RETRY_DELAY)
            else:
                print(f"Failed {func.__name__} after {MAX_RETRIES} attempts: {error_str}")
                return None


def _search_pubmed_with_date_splitting(query: str, target_count: int, use_cache: bool = True) -> List[str]:
    """
    Search PubMed for large result sets by splitting into date ranges.
    This works around PubMed's 10K limit per search.
    
    Args:
        query: PubMed search query
        target_count: Target number of PMIDs to retrieve
        use_cache: Whether to cache results
        
    Returns:
        List of PMIDs
    """
    from datetime import datetime
    from .query_cache import QueryCache
    
    # Define date ranges (yearly splits going back to 1950)
    current_year = datetime.now().year
    all_pmids = set()  # Use set to avoid duplicates
    
    print(f"Retrieving {target_count:,} papers by splitting into yearly ranges...")
    
    # Try yearly ranges from most recent to oldest
    for year in range(current_year, 1949, -1):
        # Add date filter to query
        year_query = f"({query}) AND {year}[pdat]"
        
        print(f"  Searching year {year}...")
        
        # Search this year's results
        handle = safe_ncbi_call(
            Entrez.esearch,
            db="pubmed",
            term=year_query,
            retmax=0
        )
        
        if not handle:
            continue
            
        record = Entrez.read(handle)
        handle.close()
        
        year_count = int(record["Count"])
        
        if year_count == 0:
            continue
        
        print(f"    Year {year}: {year_count:,} papers")
        
        # If this year has <10K results, fetch them directly
        if year_count <= 10000:
            # Fetch all for this year
            year_handle = safe_ncbi_call(
                Entrez.esearch,
                db="pubmed",
                term=year_query,
                retmax=min(year_count, 10000),
                sort="relevance"
            )
            
            if year_handle:
                year_record = Entrez.read(year_handle)
                year_handle.close()
                year_pmids = year_record["IdList"]
                all_pmids.update(year_pmids)
                print(f"      Retrieved {len(year_pmids):,} PMIDs (total: {len(all_pmids):,})")
        else:
            # Year has >10K, split by month
            print(f"      Year {year} has >10K results, splitting by month...")
            for month in range(1, 13):
                month_query = f"({query}) AND {year}/{month:02d}[pdat]"
                
                month_handle = safe_ncbi_call(
                    Entrez.esearch,
                    db="pubmed",
                    term=month_query,
                    retmax=10000,
                    sort="relevance"
                )
                
                if month_handle:
                    month_record = Entrez.read(month_handle)
                    month_handle.close()
                    month_pmids = month_record["IdList"]
                    if month_pmids:
                        all_pmids.update(month_pmids)
                        print(f"        {year}/{month:02d}: +{len(month_pmids)} PMIDs (total: {len(all_pmids):,})")
        
        # Stop if we've retrieved enough
        if len(all_pmids) >= target_count:
            print(f"  Reached target count, stopping...")
            break
        
        # Delay between years to respect rate limits (increased for safety)
        time.sleep(0.5)  # Was 0.3, now 0.5 for better rate limiting
    
    print(f"Successfully retrieved {len(all_pmids):,} unique PMIDs via date splitting")
    
    # Cache the results
    pmid_list = list(all_pmids)
    if use_cache:
        cache = QueryCache()
        cache.set(query, pmid_list)
    
    return pmid_list


def search_pubmed(query: str, max_results: int = 50000, use_cache: bool = True) -> List[str]:
    """
    Search PubMed with a query and return list of PMIDs.
    For >10K results, uses date-based splitting.
    Caches results to avoid re-fetching for identical queries.
    
    Args:
        query: PubMed search query
        max_results: Maximum number of results to retrieve
        use_cache: Whether to use cached results (default: True)
        
    Returns:
        List of PMIDs
    """
    from .query_cache import QueryCache
    
    Entrez.email = ENTREZ_EMAIL
    Entrez.api_key = ENTREZ_API_KEY
    
    # Check cache first
    if use_cache:
        cache = QueryCache()
        cached_pmids = cache.get(query)
        if cached_pmids is not None:
            # Respect max_results even with cached data
            if len(cached_pmids) > max_results:
                print(f"  Limiting cached results to {max_results:,} PMIDs")
                return cached_pmids[:max_results]
            return cached_pmids
    
    print(f"Searching PubMed with query...")
    
    # First, get the total count
    handle = safe_ncbi_call(
        Entrez.esearch,
        db="pubmed",
        term=query,
        retmax=0  # Just get count
    )
    
    if not handle:
        print("Search failed.")
        return []
    
    record = Entrez.read(handle)
    handle.close()
    
    total_count = int(record["Count"])
    print(f"Total papers matching query: {total_count:,}")
    
    # Determine how many to actually retrieve
    num_to_retrieve = min(total_count, max_results)
    
    if num_to_retrieve == 0:
        return []
    
    # PubMed has strict limits on retstart (~10K max)
    # For >10K results, split by date ranges automatically
    if num_to_retrieve > 10000:
        print(f"Large result set detected ({num_to_retrieve:,} papers)")
        print(f"Splitting query by date ranges to retrieve all results...")
        return _search_pubmed_with_date_splitting(query, num_to_retrieve, use_cache)
    
    batch_size = 5000  # Conservative batch size
    all_ids = []
    
    print(f"Retrieving {num_to_retrieve:,} PMIDs in batches of {batch_size:,}...")
    
    for start in range(0, num_to_retrieve, batch_size):
        # Calculate how many to fetch in this batch
        fetch_count = min(batch_size, num_to_retrieve - start)
        
        print(f"  Fetching PMIDs {start+1:,} to {start+fetch_count:,}...")
        
        # Standard approach with esearch and retstart (works for <10K results)
        handle = safe_ncbi_call(
            Entrez.esearch,
            db="pubmed",
            term=query,
            retstart=start,
            retmax=fetch_count,
            sort="relevance"
        )
        
        if not handle:
            print(f"  Failed to fetch batch starting at {start}")
            continue
        
        batch_record = Entrez.read(handle)
        handle.close()
        
        batch_ids = batch_record["IdList"]
        
        all_ids.extend(batch_ids)
        print(f"  Retrieved {len(batch_ids):,} PMIDs (total so far: {len(all_ids):,})")
        
        # Delay between batches to respect rate limits
        if start + batch_size < num_to_retrieve:
            time.sleep(0.75)  # Increased from 0.5 to 0.75 for better safety
    
    print(f"Successfully retrieved {len(all_ids):,} PMIDs")
    
    # Cache the results
    if use_cache:
        cache = QueryCache()
        cache.set(query, all_ids)
    
    return all_ids


def search_pubmed_by_dois(dois: List[str]) -> Dict[str, str]:
    """
    Search PubMed for papers by their DOIs and return mapping of DOI to PMID.
    Uses batch searching for improved performance.
    
    Args:
        dois: List of DOIs
        
    Returns:
        Dictionary mapping DOI to PMID (only for papers found in PubMed)
    """
    Entrez.email = ENTREZ_EMAIL
    Entrez.api_key = ENTREZ_API_KEY
    
    doi_to_pmid = {}
    not_found = []
    
    print(f"Searching PubMed for {len(dois)} DOIs using batch search...")
    
    # Process DOIs in batches for better performance
    batch_size = 10  # Search multiple DOIs at once
    
    for batch_start in range(0, len(dois), batch_size):
        batch_end = min(batch_start + batch_size, len(dois))
        batch_dois = dois[batch_start:batch_end]
        
        if (batch_start // batch_size + 1) % 10 == 0:
            print(f"  Processed {batch_start}/{len(dois)} DOIs...")
        
        # Create a combined query for all DOIs in the batch
        # Use OR to search for multiple DOIs at once
        query_parts = [f'"{doi}"[DOI]' for doi in batch_dois]
        combined_query = " OR ".join(query_parts)
        
        # Search for all DOIs in the batch
        handle = safe_ncbi_call(
            Entrez.esearch,
            db="pubmed",
            term=combined_query,
            retmax=batch_size
        )
        
        if not handle:
            not_found.extend(batch_dois)
            continue
        
        try:
            record = Entrez.read(handle)
            handle.close()
            
            if record["IdList"]:
                # We found some papers, now fetch their metadata to match DOIs to PMIDs
                pmids = record["IdList"]
                
                # Fetch metadata to get DOIs for each PMID
                metadata_handle = safe_ncbi_call(Entrez.efetch, db="pubmed", id=",".join(pmids), retmode="xml")
                if metadata_handle:
                    try:
                        metadata_records = Entrez.read(metadata_handle)
                        metadata_handle.close()
                        
                        # Extract DOI-PMID mappings from metadata
                        for article in metadata_records.get('PubmedArticle', []):
                            pmid = str(article['MedlineCitation']['PMID'])
                            pubmed_data = article['PubmedData']
                            
                            # Find DOI in article IDs
                            for id_item in pubmed_data.get('ArticleIdList', []):
                                id_str = str(id_item)
                                id_type = id_item.attributes.get('IdType') if hasattr(id_item, 'attributes') else None
                                if id_type and id_type.lower() == 'doi':
                                    article_doi = id_str.lower().strip()
                                    
                                    # Check if this DOI is in our batch
                                    for search_doi in batch_dois:
                                        if search_doi.lower().strip() == article_doi:
                                            doi_to_pmid[search_doi] = pmid
                                            break
                    except Exception as e:
                        print(f"Error processing batch metadata: {e}")
                        not_found.extend(batch_dois)
            else:
                not_found.extend(batch_dois)
                
        except Exception as e:
            print(f"Error processing DOI batch: {e}")
            not_found.extend(batch_dois)
    
    # Find DOIs that weren't matched
    matched_dois = set(doi_to_pmid.keys())
    all_dois = set(dois)
    not_found_set = all_dois - matched_dois
    
    print(f"\nFound {len(doi_to_pmid)} papers in PubMed")
    if not_found_set:
        print(f"Not found in PubMed: {len(not_found_set)} DOIs")
    
    return doi_to_pmid


def extract_pubmed_metadata_batch(pmids: List[str]) -> Dict[str, PaperMetadata]:
    """
    Extract metadata from PubMed for multiple PMIDs in a single API call.
    This is much faster than individual calls.
    
    Args:
        pmids: List of PubMed IDs (up to 200 recommended, 500 max)
        
    Returns:
        Dictionary mapping PMID to PaperMetadata object
    """
    if not pmids:
        return {}
    
    Entrez.email = ENTREZ_EMAIL
    Entrez.api_key = ENTREZ_API_KEY
    
    # Join PMIDs with commas for batch fetch
    pmid_string = ",".join(pmids)
    
    handle = safe_ncbi_call(Entrez.efetch, db="pubmed", id=pmid_string, retmode="xml")
    if handle is None:
        return {}
    
    try:
        records = Entrez.read(handle)
        handle.close()
    except Exception as e:
        print(f"Failed to parse PubMed batch records: {str(e)}")
        return {}
    
    results = {}
    
    # Process regular PubmedArticle entries
    for article in records.get('PubmedArticle', []):
        pmid = None  # Track PMID for error reporting
        try:
            medline = article['MedlineCitation']
            pubmed_data = article['PubmedData']
            
            # Get PMID
            pmid = str(medline['PMID'])
            
            # Initialize metadata object
            metadata = PaperMetadata(pmid=pmid)
            
            # Extract DOI and PMCID
            pmcids = []
            for id_item in pubmed_data.get('ArticleIdList', []):
                id_str = str(id_item)
                id_type = id_item.attributes.get('IdType') if hasattr(id_item, 'attributes') else None
                if id_str.startswith('PMC'):
                    pmcids.append(id_str)
                elif id_type and id_type.lower() == 'doi':
                    metadata.doi = id_str.strip()
            
            # Store the first PMC ID (if any)
            if pmcids:
                metadata.pmcid = pmcids[0]
                metadata.is_full_text_pmc = True
            
            # Extract title
            article_data = medline.get('Article', {})
            if 'ArticleTitle' in article_data:
                metadata.title = str(article_data['ArticleTitle'])
            
            # Extract abstract
            if 'Abstract' in article_data:
                abstract_parts = article_data['Abstract'].get('AbstractText', [])
                if abstract_parts:
                    abstract_text = []
                    for part in abstract_parts:
                        if hasattr(part, 'attributes') and 'Label' in part.attributes:
                            abstract_text.append(f"{part.attributes['Label']}: {str(part)}")
                        else:
                            abstract_text.append(str(part))
                    metadata.abstract = clean_abstract(' '.join(abstract_text))
            
            # Extract MeSH terms
            mesh_list = medline.get('MeshHeadingList', [])
            metadata.mesh_terms = [str(mesh['DescriptorName']) for mesh in mesh_list]
            
            # Extract keywords
            keyword_list = medline.get('KeywordList', [])
            if keyword_list:
                metadata.keywords = [str(kw) for kw in keyword_list[0]]
            
            # Extract authors
            author_list = article_data.get('AuthorList', [])
            authors = []
            for author in author_list:
                if 'LastName' in author and 'Initials' in author:
                    authors.append(f"{author['LastName']} {author['Initials']}")
                elif 'CollectiveName' in author:
                    authors.append(str(author['CollectiveName']))
            metadata.authors = authors
            
            # Extract publication date
            pub_date = article_data.get('Journal', {}).get('JournalIssue', {}).get('PubDate', {})
            if 'Year' in pub_date:
                metadata.year = str(pub_date['Year'])
                month = pub_date.get('Month', '01')
                day = pub_date.get('Day', '01')
                # Convert month name to number if necessary
                month_map = {
                    'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                    'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                    'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
                }
                if month in month_map:
                    month = month_map[month]
                metadata.date_published = f"{metadata.year}-{month}-{day}"
            
            # Extract journal
            if 'Journal' in article_data:
                journal_data = article_data['Journal']
                if 'Title' in journal_data:
                    metadata.journal = str(journal_data['Title'])
            
            results[pmid] = metadata
            
        except Exception as e:
            if pmid:
                print(f"Failed to parse article PMID {pmid} in batch: {str(e)}")
            else:
                print(f"Failed to parse article in batch (PMID unknown): {str(e)}")
            continue
    
    # Process PubmedBookArticle entries (book chapters, etc.)
    for book_article in records.get('PubmedBookArticle', []):
        pmid = None
        try:
            book_doc = book_article.get('BookDocument', {})
            pubmed_book_data = book_article.get('PubmedBookData', {})
            
            # Get PMID from ArticleIdList
            article_ids = pubmed_book_data.get('ArticleIdList', [])
            for id_item in article_ids:
                if hasattr(id_item, 'attributes') and id_item.attributes.get('IdType') == 'pubmed':
                    pmid = str(id_item)
                    break
            
            if not pmid:
                # Try alternative location
                pmid_list = [str(id_item) for id_item in article_ids]
                if pmid_list:
                    pmid = pmid_list[0]  # Use first ID as fallback
            
            if not pmid:
                continue
            
            # Initialize metadata object
            metadata = PaperMetadata(pmid=pmid)
            
            # Extract title from book chapter
            if 'ArticleTitle' in book_doc:
                metadata.title = str(book_doc['ArticleTitle'])
            
            # Extract abstract
            if 'Abstract' in book_doc:
                abstract_parts = book_doc['Abstract'].get('AbstractText', [])
                if abstract_parts:
                    abstract_text = []
                    for part in abstract_parts:
                        if hasattr(part, 'attributes') and 'Label' in part.attributes:
                            abstract_text.append(f"{part.attributes['Label']}: {str(part)}")
                        else:
                            abstract_text.append(str(part))
                    metadata.abstract = clean_abstract(' '.join(abstract_text))
            
            # Extract authors
            author_list = book_doc.get('AuthorList', [])
            authors = []
            for author in author_list:
                if 'LastName' in author and 'Initials' in author:
                    authors.append(f"{author['LastName']} {author['Initials']}")
                elif 'CollectiveName' in author:
                    authors.append(str(author['CollectiveName']))
            metadata.authors = authors
            
            # Extract publication date
            pub_date_list = pubmed_book_data.get('History', [])
            if pub_date_list:
                for pub_date_entry in pub_date_list:
                    if hasattr(pub_date_entry, 'attributes'):
                        if 'Year' in pub_date_entry:
                            metadata.year = str(pub_date_entry['Year'])
                            break
            
            # Extract book title as journal
            if 'Book' in book_doc:
                book_info = book_doc['Book']
                if 'BookTitle' in book_info:
                    metadata.journal = str(book_info['BookTitle'])
            
            results[pmid] = metadata
            
        except Exception as e:
            if pmid:
                print(f"Failed to parse book article PMID {pmid} in batch: {str(e)}")
            else:
                print(f"Failed to parse book article in batch (PMID unknown): {str(e)}")
            continue
    
    # Log which PMIDs were requested but not returned
    requested_pmids = set(pmids)
    returned_pmids = set(results.keys())
    missing_pmids = requested_pmids - returned_pmids
    
    if missing_pmids:
        print(f"⚠ Warning: {len(missing_pmids)} PMIDs not returned in batch: {', '.join(sorted(list(missing_pmids))[:10])}")
        if len(missing_pmids) > 10:
            print(f"  (showing first 10 of {len(missing_pmids)})")
    
    return results


def extract_pubmed_metadata(pmid: str) -> Optional[PaperMetadata]:
    """
    Extract metadata from PubMed for a given PMID.
    
    Args:
        pmid: PubMed ID
        
    Returns:
        PaperMetadata object or None if extraction failed
    """
    Entrez.email = ENTREZ_EMAIL
    Entrez.api_key = ENTREZ_API_KEY
    
    handle = safe_ncbi_call(Entrez.efetch, db="pubmed", id=pmid, retmode="xml")
    if handle is None:
        return None
    
    try:
        records = Entrez.read(handle)
        handle.close()
    except Exception as e:
        print(f"Failed to parse PubMed record for PMID {pmid}: {str(e)}")
        return None
    
    if not records['PubmedArticle']:
        return None
    
    article = records['PubmedArticle'][0]
    medline = article['MedlineCitation']
    pubmed_data = article['PubmedData']
    
    # Initialize metadata object
    metadata = PaperMetadata(pmid=pmid)
    
    # Extract DOI and PMCID
    pmcids = []
    for id_item in pubmed_data.get('ArticleIdList', []):
        id_str = str(id_item)
        id_type = id_item.attributes.get('IdType') if hasattr(id_item, 'attributes') else None
        if id_str.startswith('PMC'):
            pmcids.append(id_str)
        elif id_type and id_type.lower() == 'doi':
            metadata.doi = id_str.strip()
    
    # Store the first PMC ID (if any) for backward compatibility
    if pmcids:
        metadata.pmcid = pmcids[0]
        metadata.is_full_text_pmc = True
    
    # Extract title
    article_data = medline.get('Article', {})
    if 'ArticleTitle' in article_data:
        metadata.title = str(article_data['ArticleTitle'])
    
    # Extract abstract
    if 'Abstract' in article_data:
        abstract_parts = article_data['Abstract'].get('AbstractText', [])
        if abstract_parts:
            abstract_text = []
            for part in abstract_parts:
                if hasattr(part, 'attributes') and 'Label' in part.attributes:
                    abstract_text.append(f"{part.attributes['Label']}: {str(part)}")
                else:
                    abstract_text.append(str(part))
            metadata.abstract = clean_abstract(' '.join(abstract_text))
    
    # Extract MeSH terms
    mesh_list = medline.get('MeshHeadingList', [])
    metadata.mesh_terms = [str(mesh['DescriptorName']) for mesh in mesh_list]
    
    # Extract keywords
    keyword_list = medline.get('KeywordList', [])
    if keyword_list:
        metadata.keywords = [str(kw) for kw in keyword_list[0]]
    
    # Extract authors
    author_list = article_data.get('AuthorList', [])
    authors = []
    for author in author_list:
        if 'LastName' in author and 'Initials' in author:
            authors.append(f"{author['LastName']} {author['Initials']}")
        elif 'CollectiveName' in author:
            authors.append(str(author['CollectiveName']))
    metadata.authors = authors
    
    # Extract publication date
    pub_date = article_data.get('Journal', {}).get('JournalIssue', {}).get('PubDate', {})
    if 'Year' in pub_date:
        metadata.year = str(pub_date['Year'])
        month = pub_date.get('Month', '01')
        day = pub_date.get('Day', '01')
        # Convert month name to number if necessary
        month_map = {
            'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
            'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
            'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
        }
        if month in month_map:
            month = month_map[month]
        metadata.date_published = f"{metadata.year}-{month}-{day}"
    
    # Extract journal
    if 'Journal' in article_data:
        journal_data = article_data['Journal']
        if 'Title' in journal_data:
            metadata.journal = str(journal_data['Title'])
    
    return metadata


def has_meaningful_content(sections_dict: Dict[str, str], full_text: str) -> bool:
    """
    Check if extracted content has meaningful sections beyond just metadata/boilerplate.
    
    Args:
        sections_dict: Dictionary of section names to content
        full_text: Full text string
        
    Returns:
        True if content appears to be a real full text article, False otherwise
    """
    # Boilerplate/metadata sections that don't count as "full text"
    BOILERPLATE_SECTIONS = {
        'conflict of interest', 'conflicts of interest', 'competing interests',
        'acknowledgment', 'acknowledgments', 'acknowledgement', 'acknowledgements',
        'funding', 'financial disclosure', 'author contributions',
        'data availability', 'supplementary material', 'supporting information',
        'abbreviations', 'keywords', 'copyright', 'license',
        'author information', 'correspondence', 'ethics', 'consent'
    }
    
    # Meaningful sections that indicate real content
    MEANINGFUL_SECTIONS = {
        'introduction', 'background', 'methods', 'methodology', 'materials',
        'results', 'discussion', 'conclusion', 'analysis', 'findings',
        'literature review', 'theory', 'hypothesis', 'experiment',
        'case study', 'data', 'implementation', 'evaluation'
    }
    
    if not sections_dict:
        # No sections - check length only
        return len(full_text.strip()) > 2000
    
    # Count meaningful vs boilerplate sections
    meaningful_count = 0
    boilerplate_count = 0
    substantial_sections = 0  # Sections with > 500 chars
    
    for section_name, section_content in sections_dict.items():
        section_lower = section_name.lower()
        content_length = len(section_content.strip())
        
        # Skip abstract for this analysis
        if 'abstract' in section_lower:
            continue
        
        # Check if it's a boilerplate section
        is_boilerplate = any(bp in section_lower for bp in BOILERPLATE_SECTIONS)
        if is_boilerplate:
            boilerplate_count += 1
            continue
        
        # Check if it's a meaningful section
        is_meaningful = any(ms in section_lower for ms in MEANINGFUL_SECTIONS)
        if is_meaningful:
            meaningful_count += 1
        
        # Count substantial sections (regardless of name)
        if content_length > 500:
            substantial_sections += 1
    
    # Decision logic:
    # 1. If we have at least 1 meaningful section with substantial content, accept
    # 2. If we have at least 3 substantial sections (even without clear names), accept
    # 3. If only boilerplate sections found, reject
    # 4. Fallback to length check
    
    # Accept if we have at least 1 meaningful section (regardless of count)
    if meaningful_count >= 1 and substantial_sections >= 1:
        return True
    
    # Accept if we have many substantial sections (even without meaningful names)
    if substantial_sections >= 3 and boilerplate_count < substantial_sections:
        return True
    
    # Reject if we only found boilerplate
    if boilerplate_count > 0 and meaningful_count == 0 and substantial_sections < 3:
        return False
    
    # Reject if we have very few substantial sections
    if substantial_sections < 2:
        return False
    
    # Fallback: check total length
    return len(full_text.strip()) > 3000


def scrape_pmc_html(pmcid: str) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    """
    Scrape full text from PMC HTML page as a fallback when XML parsing fails or finds only abstract.
    
    Args:
        pmcid: PubMed Central ID (with or without 'PMC' prefix)
        
    Returns:
        Tuple of (full_text, sections_dict) or (None, None) if scraping fails
    """
    pmc_number = pmcid.replace("PMC", "") if pmcid.startswith("PMC") else pmcid
    url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_number}/"
    
    try:
        print(f"  Attempting HTML scraping from {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the main article content
        full_text = ""
        sections_dict = {}
        
        # Try different methods to find the article body
        body = soup.find('div', class_='jig-ncbiinpagenav')
        if not body:
            body = soup.find('article')
        if not body:
            body = soup.find('div', class_='article')
        if not body:
            body = soup.find('div', {'id': 'article'})
        
        if not body:
            print(f"  ✗ Could not find article body in HTML")
            return None, None
        
        # Extract sections - use recursive search to find all sections
        for section in body.find_all(['div', 'section'], recursive=True):
            # Get section title
            title_elem = section.find(['h2', 'h3', 'h4', 'title'])
            section_title = None
            if title_elem:
                section_title = title_elem.get_text().strip()
                if section_title and len(section_title) < 200:
                    full_text += f"\n## {section_title}\n\n"
            
            # Get paragraphs in this section (not recursive to avoid duplicates)
            section_content = ""
            for p in section.find_all('p', recursive=False):
                text = p.get_text().strip()
                if text and len(text) > 30:
                    full_text += text + "\n\n"
                    section_content += text + "\n\n"
            
            # Store section if we have content
            if section_title and section_content.strip():
                sections_dict[section_title] = section_content.strip()
        
        # If no structured sections found, try to get all paragraphs
        if not full_text.strip():
            for p in body.find_all('p'):
                text = p.get_text().strip()
                if text and len(text) > 30:
                    full_text += text + "\n\n"
        
        if full_text.strip() and len(full_text) > 500:
            print(f"  ✓ HTML scraping successful: {len(full_text)} characters")
            # Clean the text
            cleaned_full_text = clean_text_comprehensive(full_text.strip(), remove_references=True)
            cleaned_sections = {}
            for section_name, section_content in sections_dict.items():
                cleaned_sections[section_name] = clean_text_comprehensive(section_content, remove_references=True)
            return cleaned_full_text, cleaned_sections
        else:
            print(f"  ✗ HTML scraping found insufficient content")
            return None, None
            
    except Exception as e:
        print(f"  ✗ HTML scraping failed: {str(e)}")
        return None, None


def extract_pmc_fulltext(pmcid: str) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    """
    Extract full text from PubMed Central, both as flat text and structured by sections.
    
    Args:
        pmcid: PubMed Central ID (with or without 'PMC' prefix)
        
    Returns:
        Tuple of (cleaned_flat_text, sections_dict) where sections_dict is a dictionary
        mapping section names to their content
    """
    Entrez.email = ENTREZ_EMAIL
    Entrez.api_key = ENTREZ_API_KEY
    
    # Normalize PMCID format
    pmcid_stripped = pmcid.replace("PMC", "") if pmcid.startswith("PMC") else pmcid
    
    handle = safe_ncbi_call(Entrez.efetch, db="pmc", id=pmcid_stripped, rettype="full", retmode="xml")
    if handle is None:
        return None, None
    
    try:
        records = handle.read()
        handle.close()
        if isinstance(records, bytes):
            records = records.decode("utf-8")
        root = ET.fromstring(records)
    except Exception as e:
        print(f"Failed to parse PMC XML for PMCID {pmcid}: {str(e)}")
        return None, None
    
    # Find article tag
    article_tag = root.find('.//article') or (root if root.tag == 'article' else None)
    if not article_tag and root.find('.//pmc-articleset') is not None:
        article_tag = root.find('.//pmc-articleset/article')
    if not article_tag:
        print(f"No <article> tag found in XML for PMCID {pmcid}!")
        return None, None
    
    # Initialize full text and sections dictionary
    full_text = ""
    sections_dict = {}
    has_body_content = False  # Track if we have actual body content (not just abstract)
    
    # Extract abstract first (but don't add to full_text yet)
    abstract = article_tag.find('.//abstract')
    abstract_text = ""
    if abstract is not None:
        abstract_text = ' '.join(abstract.itertext())
        # Don't add to full_text yet - only add if we have body content
    
    # Extract sections recursively with section tracking
    def extract_all_sections(parent, lvl=1, section_path=""):
        text = ''
        section_content = ''
        sect_title = parent.find('./title')
        
        # Get section title
        section_name = ''.join(sect_title.itertext()).strip() if sect_title is not None else f"Section {lvl}"
        
        # Create section header for flat text
        if sect_title is not None:
            text += f"{'#' * lvl} {section_name}\n\n"
            
        # Extract paragraphs
        for p in parent.findall('./p'):
            paragraph_text = ''.join(p.itertext()).strip() + '\n\n'
            text += paragraph_text
            section_content += paragraph_text
            
        # Process subsections
        for s in parent.findall('./sec'):
            # Create nested section path
            subsection_path = f"{section_path}/{section_name}" if section_path else section_name
            subsection_text, subsection_dict = extract_all_sections(s, lvl=lvl+1, section_path=subsection_path)
            text += subsection_text
            
            # Add subsections to sections dictionary
            sections_dict.update(subsection_dict)
        
        # Add this section to the dictionary
        if section_content.strip():
            full_section_name = f"{section_path}/{section_name}" if section_path else section_name
            sections_dict[full_section_name] = section_content.strip()
            
        return text, {}
    
    # Extract body - try multiple approaches as PMC XML structure varies
    body = article_tag.find('.//body')
    
    if body is not None:
        # Standard approach: body element exists
        # Process main body sections
        for top_sec in body.findall('./sec'):
            section_text, _ = extract_all_sections(top_sec, lvl=1)
            if section_text.strip():
                full_text += section_text
                has_body_content = True
            
        # Handle paragraphs directly under body (not in sections)
        body_paragraphs = ''
        for p in body.findall('./p'):
            body_paragraphs += ''.join(p.itertext()).strip() + '\n\n'
            
        if body_paragraphs.strip():
            full_text += body_paragraphs
            sections_dict['Main'] = body_paragraphs.strip()
            has_body_content = True
    else:
        # Alternative approach: no body element, try to find sections elsewhere
        # Some PMC articles have sections directly under article or in front/back
        print(f"No <body> element found for PMCID {pmcid}, trying alternative structures...")
        
        # Try finding sections directly under article
        for top_sec in article_tag.findall('.//sec'):
            section_text, _ = extract_all_sections(top_sec, lvl=1)
            if section_text.strip():
                full_text += section_text
                has_body_content = True
        
        # Try finding paragraphs directly (but exclude abstract paragraphs)
        # Only look for paragraphs NOT inside the abstract element
        if abstract is not None:
            # Get all paragraphs except those in abstract
            all_paragraphs = article_tag.findall('.//p')
            abstract_paragraphs = abstract.findall('.//p')
            body_paragraphs_list = [p for p in all_paragraphs if p not in abstract_paragraphs]
        else:
            body_paragraphs_list = article_tag.findall('.//p')
        
        for p in body_paragraphs_list:
            paragraph_text = ''.join(p.itertext()).strip()
            if paragraph_text and len(paragraph_text) > 30:  # Require substantial text
                full_text += paragraph_text + '\n\n'
                has_body_content = True
    
    # Extract tables
    if EXTRACT_TABLES:
        tables = article_tag.findall('.//table-wrap')
        if tables:
            tables_section = "\n## TABLES\n\n"
            tables_content = ""
            
            for table_idx, table in enumerate(tables, 1):
                caption = table.find('.//caption')
                if caption is not None:
                    table_text = f"**Table {table_idx}:** {' '.join(caption.itertext())}\n"
                    tables_section += table_text
                    tables_content += table_text
                    
                table_content = table.find('.//table')
                if table_content is not None:
                    table_data = ' '.join(table_content.itertext()) + "\n\n"
                    tables_section += table_data
                    tables_content += table_data
            
            if tables_content.strip():
                full_text += tables_section
                sections_dict['Tables'] = tables_content.strip()
                has_body_content = True
    
    # Extract figures
    if EXTRACT_FIGURES:
        figures = article_tag.findall('.//fig')
        if figures:
            figures_section = "\n## FIGURES\n\n"
            figures_content = ""
            
            for fig_idx, figure in enumerate(figures, 1):
                caption = figure.find('.//caption')
                if caption is not None:
                    figure_text = f"**Figure {fig_idx}:** {' '.join(caption.itertext())}\n\n"
                    figures_section += figure_text
                    figures_content += figure_text
            
            if figures_content.strip():
                full_text += figures_section
                sections_dict['Figures'] = figures_content.strip()
                has_body_content = True
    
    # If we still have no content, try more aggressive extraction methods
    if not has_body_content:
        print(f"No structured content found for PMCID {pmcid}, trying fallback extraction...")
        
        # Try 1: Extract all text from body element
        body = article_tag.find('.//body')
        if body is not None:
            body_text = ' '.join(body.itertext()).strip()
            if body_text and len(body_text) > 100:  # Require substantial text
                full_text += body_text
                sections_dict['Body'] = body_text
                has_body_content = True
                print(f"  ✓ Extracted {len(body_text)} chars from <body>")
        
        # Try 2: If still nothing, extract from entire article (excluding abstract)
        if not has_body_content:
            # Try front/back elements (some articles use these)
            for section_name in ['front', 'back']:
                section_elem = article_tag.find(f'.//{section_name}')
                if section_elem is not None:
                    section_text = ' '.join(section_elem.itertext()).strip()
                    if section_text and len(section_text) > 100:
                        full_text += f"\n\n## {section_name.upper()}\n{section_text}"
                        sections_dict[section_name.capitalize()] = section_text
                        has_body_content = True
                        print(f"  ✓ Extracted {len(section_text)} chars from <{section_name}>")
        
        # Try 3: Last resort - extract all text from article (excluding abstract)
        if not has_body_content:
            all_text = ' '.join(article_tag.itertext()).strip()
            # Remove abstract text if present
            if abstract_text and abstract_text in all_text:
                all_text = all_text.replace(abstract_text, '').strip()
            
            if all_text and len(all_text) > 200:  # Require substantial text beyond abstract
                full_text += all_text
                sections_dict['Content'] = all_text
                has_body_content = True
                print(f"  ✓ Extracted {len(all_text)} chars from entire article")
    
    # Only return full text if we have actual body content (not just abstract)
    # Use smart validation to check for meaningful content
    body_text_length = len(full_text.strip())
    has_meaningful = has_meaningful_content(sections_dict, full_text)
    
    if not has_meaningful and body_text_length > 0:
        # Log why content was rejected
        section_names = list(sections_dict.keys())
        print(f"  Content validation failed for PMCID {pmcid}:")
        print(f"    - Length: {body_text_length} chars")
        print(f"    - Sections: {section_names}")
    
    if has_body_content and has_meaningful:
        # Now prepend abstract to the body content
        if abstract_text:
            full_text = f"ABSTRACT:\n{abstract_text}\n\n{full_text}"
            sections_dict['Abstract'] = abstract_text
        
        cleaned_full_text = clean_text_comprehensive(full_text.strip(), remove_references=True)
        
        # Clean each section
        cleaned_sections = {}
        for section_name, section_content in sections_dict.items():
            cleaned_sections[section_name] = clean_text_comprehensive(section_content, remove_references=True)
        
        return cleaned_full_text, cleaned_sections
    else:
        # Only abstract or insufficient content - try HTML scraping as fallback
        if abstract_text and (not has_body_content or not has_meaningful):
            if body_text_length > 0:
                print(f"Only {body_text_length} chars found for PMCID {pmcid} in XML (insufficient), trying HTML scraping...")
            else:
                print(f"Only abstract found for PMCID {pmcid} in XML, trying HTML scraping...")
            html_text, html_sections = scrape_pmc_html(pmcid)
            if html_text:
                # Prepend abstract to HTML-scraped content
                full_html_text = f"ABSTRACT:\n{abstract_text}\n\n{html_text}"
                html_sections['Abstract'] = abstract_text
                cleaned_full_text = clean_text_comprehensive(full_html_text.strip(), remove_references=True)
                cleaned_sections = {}
                for section_name, section_content in html_sections.items():
                    cleaned_sections[section_name] = clean_text_comprehensive(section_content, remove_references=True)
                return cleaned_full_text, cleaned_sections
            else:
                print(f"HTML scraping also failed for PMCID {pmcid}")
                return None, None
        else:
            print(f"No text content found for PMCID {pmcid}")
            return None, None


def extract_fulltext_by_doi(doi: str) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    """
    Attempt to extract full text using a DOI by searching for it in PubMed Central.
    
    Args:
        doi: Digital Object Identifier
        
    Returns:
        Tuple of (cleaned_flat_text, sections_dict) where sections_dict is a dictionary
        mapping section names to their content, or (None, None) if extraction failed
    """
    Entrez.email = ENTREZ_EMAIL
    Entrez.api_key = ENTREZ_API_KEY
    
    # First, search for the paper in PMC using the DOI
    handle = safe_ncbi_call(
        Entrez.esearch,
        db="pmc",
        term=f"{doi}[DOI]",
        retmax=1
    )
    
    if not handle:
        return None, None
    
    record = Entrez.read(handle)
    handle.close()
    
    if not record["IdList"]:
        return None, None
    
    # Get the PMC ID from the search results
    pmcid = record["IdList"][0]
    
    # Use the existing function to extract full text
    return extract_pmc_fulltext(pmcid)


def try_all_fulltext_sources(metadata: PaperMetadata) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    """
    Try multiple sources to retrieve full text for a paper.
    
    Args:
        metadata: Paper metadata with DOI, PMID, etc.
        
    Returns:
        Tuple of (full_text, sections) if successful, or (None, None) if all attempts fail
    """
    # 1. Try using PMC ID if available
    if metadata.pmcid:
        print(f"Trying to retrieve full text using PMCID: {metadata.pmcid}")
        full_text, sections = extract_pmc_fulltext(metadata.pmcid)
        if full_text:
            print(f"Retrieved full text using PMCID: {metadata.pmcid}")
            return full_text, sections
    
    # 2. Try using DOI if available
    if metadata.doi:
        print(f"Trying to retrieve full text using DOI: {metadata.doi}")
        full_text, sections = extract_fulltext_by_doi(metadata.doi)
        if full_text:
            print(f"Retrieved full text using DOI: {metadata.doi}")
            return full_text, sections
    
    # 3. Try searching for the paper in PMC using title and authors
    # if metadata.title and metadata.authors:
    #     print(f"Trying to retrieve full text using title and authors")
    #     # Create a search query with title and first author
    #     first_author = metadata.authors[0].split()[0] if metadata.authors else ""
    #     search_query = f"\"{metadata.title}\"[Title] AND {first_author}[Author]"
        
    #     handle = safe_ncbi_call(
    #         Entrez.esearch,
    #         db="pmc",
    #         term=search_query,
    #         retmax=1
    #     )
        
    #     if handle:
    #         record = Entrez.read(handle)
    #         handle.close()
            
    #         if record["IdList"]:
    #             pmcid = record["IdList"][0]
    #             full_text, sections = extract_pmc_fulltext(pmcid)
    #             if full_text:
    #                 print(f"Retrieved full text using title/author search, PMCID: {pmcid}")
    #                 return full_text, sections
    
    # No full text found from any source
    return None, None


def process_paper(pmid: str) -> Optional[PaperMetadata]:
    """
    Process a single paper: extract metadata and full text if available.
    
    Args:
        pmid: PubMed ID
        
    Returns:
        PaperMetadata object or None if processing failed
    """
    # Extract metadata from PubMed
    metadata = extract_pubmed_metadata(pmid)
    if metadata is None:
        return None
    
    # Get all PMC IDs for this paper
    pmcids = []
    handle = safe_ncbi_call(Entrez.efetch, db="pubmed", id=pmid, retmode="xml")
    if handle is not None:
        try:
            records = Entrez.read(handle)
            handle.close()
            if records['PubmedArticle']:
                article = records['PubmedArticle'][0]
                pmcids = [str(id_item) for id_item in article['PubmedData'].get('ArticleIdList', [])
                         if str(id_item).startswith('PMC')]
        except Exception as e:
            print(f"Error getting PMC IDs for PMID {pmid}: {str(e)}")
    
    # Try all available methods to get full text
    full_text, sections = try_all_fulltext_sources(metadata)
    if full_text:
        metadata.full_text = full_text
        metadata.full_text_sections = sections if sections else {}
        metadata.is_full_text_pmc = True
    
    # If still no full text and we have a DOI, try direct DOI search
    if not metadata.has_full_text() and metadata.doi:
        print(f"Attempting direct DOI search for full text: {metadata.doi}")
        # Search for the paper in PMC using the DOI directly
        handle = safe_ncbi_call(
            Entrez.esearch,
            db="pmc",
            term=f"{metadata.doi}[DOI]",
            retmax=1
        )
        
        if handle:
            record = Entrez.read(handle)
            handle.close()
            
            if record["IdList"]:
                pmcid = record["IdList"][0]
                print(f"Found PMC ID from direct DOI search: {pmcid}")
                full_text, sections = extract_pmc_fulltext(pmcid)
                if full_text:
                    metadata.pmcid = f"PMC{pmcid}" if not pmcid.startswith("PMC") else pmcid
                    metadata.full_text = full_text
                    metadata.full_text_sections = sections if sections else {}
                    metadata.is_full_text_pmc = True
                    print(f"Successfully retrieved full text using direct DOI search")
    
    return metadata
