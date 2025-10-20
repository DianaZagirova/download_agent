#!/usr/bin/env python3
"""
bioRxiv metadata and full-text extractor
"""
import time
import requests
import re
from typing import Optional, List, Tuple, Dict
from datetime import datetime
import PyPDF2
import io

from .models import PaperMetadata
from .text_cleaner import clean_text_comprehensive
from .config import MAX_RETRIES, RETRY_DELAY


def search_biorxiv_europepmc(query: str, max_results: int = 5000, server: str = "biorxiv") -> List[Dict]:
    """
    Search bioRxiv/medRxiv via Europe PMC API (supports proper keyword search).
    
    Args:
        query: Search query string (supports Boolean operators: AND, OR, NOT)
        max_results: Maximum number of results to retrieve
        server: 'biorxiv' or 'medrxiv' (filters results by source)
        
    Returns:
        List of paper metadata dictionaries
    """
    print(f"Searching {server} via Europe PMC for: {query}")
    
    base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    all_papers = []
    page_size = 100  # Max per request
    
    # Construct query with preprint filter
    # SRC:PPR filters for preprints (includes bioRxiv, medRxiv)
    if server == "medrxiv":
        full_query = f"({query}) AND (SRC:MED)"  # MED = medRxiv
    else:
        full_query = f"({query}) AND (SRC:PPR)"  # PPR = preprints (bioRxiv + medRxiv)
    
    cursor = "*"
    
    while len(all_papers) < max_results:
        params = {
            "query": full_query,
            "format": "json",
            "pageSize": page_size,
            "cursorMark": cursor,
            "resultType": "core"  # Get full metadata
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                results = data.get('resultList', {}).get('result', [])
                
                if not results:
                    print("No more papers found.")
                    break
                
                # Convert Europe PMC format to bioRxiv-compatible format
                for paper in results:
                    source = paper.get('source', 'PPR')
                    
                    paper_dict = {
                        'doi': paper.get('doi', ''),
                        'title': paper.get('title', ''),
                        'abstract': paper.get('abstractText', ''),
                        'authors': '; '.join([
                            f"{a.get('lastName', '')}, {a.get('firstName', '')}" 
                            for a in paper.get('authorList', {}).get('author', [])
                        ]) if 'authorList' in paper else '',
                        'date': paper.get('firstPublicationDate', ''),
                        'server': source,
                        'pmid': paper.get('pmid', ''),
                        'pmcid': paper.get('pmcid', ''),
                    }
                    all_papers.append(paper_dict)
                
                print(f"  Fetched {len(all_papers)} papers...")
                
                # Check for next page
                next_cursor = data.get('nextCursorMark')
                if not next_cursor or next_cursor == cursor:
                    break
                
                cursor = next_cursor
                time.sleep(0.2)  # Rate limiting
                
            elif response.status_code == 404:
                print("No papers found.")
                break
            else:
                print(f"API error: {response.status_code}")
                break
                
        except Exception as e:
            print(f"Error fetching papers: {e}")
            break
    
    print(f"Found {len(all_papers)} papers matching criteria")
    return all_papers[:max_results]


def search_biorxiv(query: str, max_results: int = 5000, server: str = "biorxiv") -> List[Dict]:
    """
    Search bioRxiv/medRxiv for papers matching a query.
    Uses Europe PMC API for proper keyword search support.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to retrieve
        server: 'biorxiv' or 'medrxiv'
        
    Returns:
        List of paper metadata dictionaries
    """
    return search_biorxiv_europepmc(query, max_results, server)


def extract_biorxiv_metadata(paper_dict: Dict) -> Optional[PaperMetadata]:
    """
    Extract metadata from bioRxiv/Europe PMC API response.
    
    Args:
        paper_dict: Dictionary from bioRxiv or Europe PMC API
        
    Returns:
        PaperMetadata object or None
    """
    try:
        # bioRxiv uses DOI as primary identifier
        doi = paper_dict.get('doi')
        if not doi:
            return None
        
        # Handle authors - can be string (semicolon-separated) or already a list
        authors = paper_dict.get('authors', '')
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.split(';') if a.strip()]
        elif not isinstance(authors, list):
            authors = []
        
        # Get publication date
        date_published = paper_dict.get('date') or paper_dict.get('firstPublicationDate')
        year = date_published[:4] if date_published and len(date_published) >= 4 else None
        
        # Determine journal/server
        server = paper_dict.get('server', 'biorxiv')
        if isinstance(server, str):
            if 'medrxiv' in server.lower():
                journal = "medRxiv (preprint)"
            elif 'biorxiv' in server.lower():
                journal = "bioRxiv (preprint)"
            else:
                journal = f"{server} (preprint)"
        else:
            journal = "bioRxiv (preprint)"
        
        # Extract basic metadata
        metadata = PaperMetadata(
            pmid=paper_dict.get('pmid') or doi,  # Use PMID if available, else DOI
            pmcid=paper_dict.get('pmcid'),
            doi=doi,
            title=paper_dict.get('title'),
            abstract=paper_dict.get('abstract') or paper_dict.get('abstractText'),
            authors=authors,
            date_published=date_published,
            year=year,
            journal=journal,
        )
        
        # Add bioRxiv-specific info to collection_date field
        metadata.collection_date = datetime.now().isoformat()
        
        return metadata
        
    except Exception as e:
        print(f"Error extracting metadata: {e}")
        return None


def download_biorxiv_fulltext_from_url(pdf_url: str) -> Optional[str]:
    """
    Download and extract text from a PDF URL.
    
    Args:
        pdf_url: Direct URL to PDF file
        
    Returns:
        Extracted text or None
    """
    try:
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(pdf_url, timeout=60)
                
                if response.status_code == 200:
                    # Extract text from PDF
                    pdf_file = io.BytesIO(response.content)
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    
                    text_parts = []
                    for page in pdf_reader.pages:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                    
                    full_text = '\n\n'.join(text_parts)
                    
                    # Clean the text
                    full_text = clean_text_comprehensive(full_text)
                    
                    return full_text
                    
                elif response.status_code == 404:
                    return None
                    
                else:
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                    else:
                        return None
                        
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"Error downloading PDF from {pdf_url}: {e}")
                    return None
                    
    except Exception as e:
        print(f"Error in PDF download from {pdf_url}: {e}")
        return None


def download_biorxiv_fulltext_pdf(doi: str, server: str = "biorxiv") -> Optional[str]:
    """
    Download and extract text from bioRxiv PDF.
    
    Args:
        doi: Paper DOI
        server: 'biorxiv' or 'medrxiv'
        
    Returns:
        Extracted text or None
    """
    try:
        # Construct PDF URL
        # Format: https://www.biorxiv.org/content/10.1101/2024.01.01.123456v1.full.pdf
        pdf_url = f"https://www.{server}.org/content/{doi}.full.pdf"
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(pdf_url, timeout=60)
                
                if response.status_code == 200:
                    # Extract text from PDF
                    pdf_file = io.BytesIO(response.content)
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    
                    text_parts = []
                    for page in pdf_reader.pages:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                    
                    full_text = '\n\n'.join(text_parts)
                    
                    # Clean the text
                    full_text = clean_text_comprehensive(full_text)
                    
                    return full_text
                    
                elif response.status_code == 404:
                    # Try alternative URL format without version number
                    if 'v' in doi:
                        base_doi = doi.rsplit('v', 1)[0]
                        pdf_url = f"https://www.{server}.org/content/{base_doi}.full.pdf"
                        continue
                    return None
                    
                else:
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                    else:
                        return None
                        
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"Error downloading PDF for {doi}: {e}")
                    return None
                    
    except Exception as e:
        print(f"Error in PDF download for {doi}: {e}")
        return None


def try_biorxiv_fulltext(metadata: PaperMetadata, pdf_url: str = None) -> Tuple[Optional[str], Dict[str, str]]:
    """
    Try to fetch full text from bioRxiv.
    
    Args:
        metadata: PaperMetadata with DOI
        pdf_url: Optional direct PDF URL (e.g., from OpenAlex)
        
    Returns:
        Tuple of (full_text, sections_dict)
    """
    if not metadata.doi and not pdf_url:
        return None, {}
    
    # If we have a direct PDF URL (e.g., from OpenAlex), try that first
    if pdf_url:
        print(f"  Downloading full text from provided URL...")
        full_text = download_biorxiv_fulltext_from_url(pdf_url)
        if full_text:
            sections = {"main": full_text}
            return full_text, sections
    
    # Otherwise try standard bioRxiv URLs
    if metadata.doi:
        # Determine server (biorxiv or medrxiv) from DOI or journal
        server = "medrxiv" if (metadata.journal and "medrxiv" in metadata.journal.lower()) else "biorxiv"
        
        print(f"  Downloading full text for {metadata.doi}...")
        full_text = download_biorxiv_fulltext_pdf(metadata.doi, server)
        
        if full_text:
            # For bioRxiv PDFs, we don't have structured sections
            # Return as a single "main" section
            sections = {"main": full_text}
            return full_text, sections
    
    return None, {}


def process_biorxiv_paper(paper_dict: Dict) -> Optional[PaperMetadata]:
    """
    Process a single bioRxiv paper: extract metadata and full text.
    
    Args:
        paper_dict: Dictionary from bioRxiv API
        
    Returns:
        PaperMetadata or None
    """
    # Extract metadata
    metadata = extract_biorxiv_metadata(paper_dict)
    if not metadata:
        return None
    
    # Try to get full text
    full_text, sections = try_biorxiv_fulltext(metadata)
    if full_text:
        metadata.full_text = full_text
        metadata.full_text_sections = sections
        metadata.is_full_text_pmc = True  # Use this flag to indicate we have full text
    
    return metadata


def search_biorxiv_by_query_advanced(query: str, max_results: int = 5000, 
                                      start_date: str = None, 
                                      end_date: str = None) -> List[str]:
    """
    Advanced search using bioRxiv's collection API with date filtering.
    
    Args:
        query: Search query (will filter by keywords in title/abstract)
        max_results: Maximum number of results
        start_date: Start date in YYYY-MM-DD format (default: 2 years ago)
        end_date: End date in YYYY-MM-DD format (default: today)
        
    Returns:
        List of DOIs
    """
    papers = search_biorxiv(query, max_results)
    return [p.get('doi') for p in papers if p.get('doi')]


def get_biorxiv_paper_metadata(doi: str, server: str = "biorxiv") -> Optional[Dict]:
    """
    Fetch metadata for a specific bioRxiv paper by DOI.
    
    Args:
        doi: Paper DOI
        server: 'biorxiv' or 'medrxiv'
        
    Returns:
        Paper metadata dictionary or None
    """
    url = f"https://api.biorxiv.org/details/{server}/{doi}"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'collection' in data and data['collection']:
                return data['collection'][0]
                
    except Exception as e:
        print(f"Error fetching metadata for {doi}: {e}")
    
    return None
