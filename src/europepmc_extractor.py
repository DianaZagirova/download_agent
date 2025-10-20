#!/usr/bin/env python3
"""
Europe PMC metadata and full-text extractor
Searches all Europe PMC content (published papers + preprints)
"""
import time
import requests
from typing import Optional, List, Dict
from datetime import datetime

from .models import PaperMetadata
from .config import MAX_RETRIES, RETRY_DELAY


def search_europepmc(query: str, max_results: int = 5000, include_preprints: bool = True) -> List[Dict]:
    """
    Search Europe PMC for papers matching a query.
    
    Args:
        query: Search query string (supports Boolean operators: AND, OR, NOT)
        max_results: Maximum number of results to retrieve
        include_preprints: If True, includes preprints; if False, only peer-reviewed
        
    Returns:
        List of paper metadata dictionaries
    """
    print(f"Searching Europe PMC for: {query}")
    if not include_preprints:
        print("(Excluding preprints - peer-reviewed only)")
    
    base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    all_papers = []
    page_size = 100  # Max per request
    
    # Construct query
    if include_preprints:
        full_query = query  # Search everything
        print("Searching: Published papers + Preprints (bioRxiv, medRxiv, etc.)")
    else:
        # Exclude preprints - only get published papers
        full_query = f"({query}) NOT SRC:PPR"
        print("Searching: Published papers only")
    
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
                
                # Convert Europe PMC format to standard format
                for paper in results:
                    source = paper.get('source', 'unknown')
                    
                    paper_dict = {
                        'doi': paper.get('doi', ''),
                        'pmid': paper.get('pmid', ''),
                        'pmcid': paper.get('pmcid', ''),
                        'title': paper.get('title', ''),
                        'abstract': paper.get('abstractText', ''),
                        'authors': '; '.join([
                            f"{a.get('lastName', '')}, {a.get('firstName', '')}" 
                            for a in paper.get('authorList', {}).get('author', [])
                        ]) if 'authorList' in paper else '',
                        'date': paper.get('firstPublicationDate', ''),
                        'year': paper.get('pubYear', ''),
                        'journal': paper.get('journalTitle', ''),
                        'source': source,
                        'is_preprint': source in ['PPR', 'MED', 'Preprints.org'],
                        'citation_count': paper.get('citedByCount', 0),
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


def extract_europepmc_metadata(paper_dict: Dict) -> Optional[PaperMetadata]:
    """
    Extract metadata from Europe PMC API response.
    
    Args:
        paper_dict: Dictionary from Europe PMC API
        
    Returns:
        PaperMetadata object or None
    """
    try:
        # Prefer DOI, fallback to PMID
        doi = paper_dict.get('doi')
        pmid = paper_dict.get('pmid')
        
        if not doi and not pmid:
            return None
        
        # Handle authors - can be string (semicolon-separated) or already a list
        authors = paper_dict.get('authors', '')
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.split(';') if a.strip()]
        elif not isinstance(authors, list):
            authors = []
        
        # Get publication date
        date_published = paper_dict.get('date')
        year = paper_dict.get('year') or (date_published[:4] if date_published and len(date_published) >= 4 else None)
        
        # Determine journal and type
        journal = paper_dict.get('journal', 'Unknown')
        source = paper_dict.get('source', '')
        is_preprint = paper_dict.get('is_preprint', False)
        
        if is_preprint:
            if 'biorxiv' in source.lower() or 'biorxiv' in journal.lower():
                journal = "bioRxiv (preprint)"
            elif 'medrxiv' in source.lower() or 'medrxiv' in journal.lower():
                journal = "medRxiv (preprint)"
            else:
                journal = f"{journal} (preprint)"
        
        # Extract basic metadata
        metadata = PaperMetadata(
            pmid=pmid or doi,  # Use PMID if available, else DOI
            pmcid=paper_dict.get('pmcid'),
            doi=doi,
            title=paper_dict.get('title'),
            abstract=paper_dict.get('abstract'),
            authors=authors,
            date_published=date_published,
            year=year,
            journal=journal,
            cited_by_count=paper_dict.get('citation_count', 0),
            source="EuropePMC"  # Mark as from Europe PMC
        )
        
        metadata.collection_date = datetime.now().isoformat()
        
        return metadata
        
    except Exception as e:
        print(f"Error extracting metadata: {e}")
        return None


def search_europepmc_by_field(field: str, value: str, max_results: int = 1000) -> List[Dict]:
    """
    Search Europe PMC by specific field.
    
    Args:
        field: Field to search (TITLE, AUTH, JOURNAL, etc.)
        value: Value to search for
        max_results: Maximum results
        
    Returns:
        List of paper dictionaries
    """
    query = f"{field}:{value}"
    return search_europepmc(query, max_results)


def search_europepmc_by_date_range(query: str, start_year: int, end_year: int, max_results: int = 5000) -> List[Dict]:
    """
    Search Europe PMC with date range filter.
    
    Args:
        query: Base search query
        start_year: Start year (e.g., 2020)
        end_year: End year (e.g., 2025)
        max_results: Maximum results
        
    Returns:
        List of paper dictionaries
    """
    date_query = f"({query}) AND PUB_YEAR:[{start_year} TO {end_year}]"
    return search_europepmc(date_query, max_results)


def get_paper_statistics(papers: List[Dict]) -> Dict:
    """
    Get statistics about a collection of papers.
    
    Args:
        papers: List of paper dictionaries
        
    Returns:
        Statistics dictionary
    """
    stats = {
        'total_papers': len(papers),
        'with_doi': sum(1 for p in papers if p.get('doi')),
        'with_pmid': sum(1 for p in papers if p.get('pmid')),
        'with_pmcid': sum(1 for p in papers if p.get('pmcid')),
        'preprints': sum(1 for p in papers if p.get('is_preprint')),
        'published': sum(1 for p in papers if not p.get('is_preprint')),
        'with_abstract': sum(1 for p in papers if p.get('abstract')),
        'total_citations': sum(p.get('citation_count', 0) for p in papers),
        'years': {}
    }
    
    # Count by year
    for paper in papers:
        year = paper.get('year', 'Unknown')
        stats['years'][year] = stats['years'].get(year, 0) + 1
    
    return stats
