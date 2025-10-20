#!/usr/bin/env python3
"""
OpenAlex metadata extractor
"""
import time
import requests
import threading
from typing import Optional
from datetime import datetime, timedelta

from .models import PaperMetadata
from .config import OPENALEX_DELAY, MAX_RETRIES, RETRY_DELAY, OPENALEX_EMAIL, OPENALEX_MAX_REQUESTS_PER_DAY


# Shared rate limiter for thread-safe API calls
_openalex_lock = threading.Lock()
_last_request_time = 0
_daily_request_count = 0
_daily_count_reset_time = datetime.now()

def _check_and_wait_rate_limit():
    """
    Thread-safe rate limiter that enforces:
    - Minimum delay between requests (OPENALEX_DELAY)
    - Daily request limit (100,000 requests/day)
    
    Should be called before making any OpenAlex API request.
    """
    global _last_request_time, _daily_request_count, _daily_count_reset_time
    
    with _openalex_lock:
        # Reset daily counter if it's a new day
        now = datetime.now()
        if now - _daily_count_reset_time > timedelta(days=1):
            _daily_request_count = 0
            _daily_count_reset_time = now
            print(f"[OpenAlex] Daily request counter reset. New day started.")
        
        # Check daily limit
        if _daily_request_count >= OPENALEX_MAX_REQUESTS_PER_DAY:
            print(f"[OpenAlex] WARNING: Daily limit of {OPENALEX_MAX_REQUESTS_PER_DAY} requests reached!")
            print(f"[OpenAlex] Waiting until next day...")
            # Calculate time until next day
            next_day = _daily_count_reset_time + timedelta(days=1)
            wait_seconds = (next_day - now).total_seconds()
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            _daily_request_count = 0
            _daily_count_reset_time = datetime.now()
        
        # Enforce minimum delay between requests
        current_time = time.time()
        time_since_last = current_time - _last_request_time
        
        if time_since_last < OPENALEX_DELAY:
            sleep_time = OPENALEX_DELAY - time_since_last
            time.sleep(sleep_time)
        
        _last_request_time = time.time()
        _daily_request_count += 1
        
        # Log progress every 100 requests
        if _daily_request_count % 100 == 0:
            print(f"[OpenAlex] Made {_daily_request_count} requests today")


def enrich_with_openalex(metadata: PaperMetadata) -> PaperMetadata:
    """
    Enrich paper metadata with OpenAlex data.
    
    Args:
        metadata: PaperMetadata object with at least DOI populated
        
    Returns:
        Updated PaperMetadata object
    """
    if not metadata.doi:
        return metadata
    
    # Clean DOI (remove URL prefix if present)
    doi = metadata.doi
    if doi.startswith('http'):
        doi = doi.split('doi.org/')[-1]
    
    # Add mailto parameter for "polite pool" access (better rate limits)
    url = f"https://api.openalex.org/works/https://doi.org/{doi}?mailto={OPENALEX_EMAIL}"
    
    # Set User-Agent header for polite pool (recommended by OpenAlex)
    headers = {
        'User-Agent': f'PubMedCollector/1.0 (mailto:{OPENALEX_EMAIL})'
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            # Thread-safe rate limiting (replaces simple sleep)
            _check_and_wait_rate_limit()
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract OpenAlex fields
                metadata.cited_by_count = data.get("cited_by_count")
                metadata.citation_normalized_percentile = data.get("citation_normalized_percentile", {}).get("value") if isinstance(data.get("citation_normalized_percentile"), dict) else data.get("citation_normalized_percentile")
                metadata.fwci = data.get("fwci")
                
                # Extract open access URL
                open_access = data.get("open_access", {})
                if open_access and isinstance(open_access, dict):
                    metadata.oa_url = open_access.get("oa_url")
                
                # Extract primary topic (store full dictionary)
                primary_topic = data.get("primary_topic")
                if primary_topic and isinstance(primary_topic, dict):
                    metadata.primary_topic = primary_topic
                    
                    # Debug log topic fields (DISABLED for large runs - uncomment if needed)
                    # topic_name = primary_topic.get('display_name')
                    # topic_subfield = primary_topic.get('subfield', {}).get('display_name') if 'subfield' in primary_topic else None
                    # topic_field = primary_topic.get('field', {}).get('display_name') if 'field' in primary_topic else None
                    # topic_domain = primary_topic.get('domain', {}).get('display_name') if 'domain' in primary_topic else None
                    # 
                    # print(f"Topic info for {metadata.doi}:")
                    # print(f"  - Topic: {topic_name}")
                    # print(f"  - Subfield: {topic_subfield}")
                    # print(f"  - Field: {topic_field}")
                    # print(f"  - Domain: {topic_domain}")
                
                metadata.openalex_retrieved = True
                return metadata
                
            elif response.status_code == 404:
                # DOI not found in OpenAlex
                return metadata
            elif response.status_code == 429:
                # Rate limit - use exponential backoff
                if attempt < MAX_RETRIES - 1:
                    backoff_time = RETRY_DELAY * (2 ** attempt)  # Exponential: 3s, 6s, 12s, 24s, 48s
                    print(f"⚠ OpenAlex rate limit (429) for DOI {doi}, waiting {backoff_time}s before retry {attempt+1}/{MAX_RETRIES}...")
                    print(f"  Consider: 1) Reducing parallel workers, 2) Increasing OPENALEX_DELAY, 3) Check daily limit")
                    time.sleep(backoff_time)
                else:
                    print(f"✗ Failed to retrieve OpenAlex data for DOI {doi} after {MAX_RETRIES} attempts (rate limited)")
                    return metadata
            else:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (1 + attempt)  # Linear backoff for other errors
                    print(f"OpenAlex API returned {response.status_code} for DOI {doi}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"Failed to retrieve OpenAlex data for DOI {doi} after {MAX_RETRIES} attempts")
                    return metadata
                    
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES - 1:
                print(f"OpenAlex request timeout for DOI {doi}, retrying...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"OpenAlex request timeout for DOI {doi} after {MAX_RETRIES} attempts")
                return metadata
                
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"Error retrieving OpenAlex data for DOI {doi}: {str(e)}, retrying...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"Failed to retrieve OpenAlex data for DOI {doi}: {str(e)}")
                return metadata
    
    return metadata


def batch_enrich_with_openalex(metadata_list: list[PaperMetadata], batch_size: int = 50) -> list[PaperMetadata]:
    """
    Enrich multiple papers with OpenAlex data using batched API calls.
    Uses OpenAlex OR syntax to fetch up to 50 DOIs per API call (50x faster!).
    See: https://blog.ourresearch.org/fetch-multiple-dois-in-one-openalex-api-request/
    
    Args:
        metadata_list: List of PaperMetadata objects
        batch_size: Number of DOIs to fetch per API call (max 50 recommended)
        
    Returns:
        List of enriched PaperMetadata objects
    """
    # Filter papers with DOIs
    papers_with_doi = [m for m in metadata_list if m.doi]
    papers_without_doi = [m for m in metadata_list if not m.doi]
    
    if not papers_with_doi:
        return metadata_list
    
    # Create DOI to metadata mapping for quick lookup
    doi_to_metadata = {}
    for metadata in papers_with_doi:
        # Clean DOI
        doi = metadata.doi
        if doi.startswith('http'):
            doi = doi.split('doi.org/')[-1]
        doi_to_metadata[doi.lower()] = metadata
    
    # Process in batches
    enriched = []
    doi_list = list(doi_to_metadata.keys())
    
    for i in range(0, len(doi_list), batch_size):
        batch_dois = doi_list[i:i+batch_size]
        
        # Build OR query: doi.org/10.1234|doi.org/10.5678|...
        doi_filter = '|'.join([f'https://doi.org/{doi}' for doi in batch_dois])
        url = f"https://api.openalex.org/works?filter=doi:{doi_filter}&mailto={OPENALEX_EMAIL}&per-page={batch_size}"
        
        headers = {
            'User-Agent': f'PubMedCollector/1.0 (mailto:{OPENALEX_EMAIL})'
        }
        
        try:
            # Thread-safe rate limiting
            _check_and_wait_rate_limit()
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                # Match results back to metadata objects
                for work in results:
                    work_doi = work.get('doi', '').replace('https://doi.org/', '').lower()
                    
                    if work_doi in doi_to_metadata:
                        metadata = doi_to_metadata[work_doi]
                        
                        # Extract OpenAlex fields
                        metadata.cited_by_count = work.get("cited_by_count")
                        metadata.citation_normalized_percentile = work.get("citation_normalized_percentile", {}).get("value") if isinstance(work.get("citation_normalized_percentile"), dict) else work.get("citation_normalized_percentile")
                        metadata.fwci = work.get("fwci")
                        
                        # Extract open access URL
                        open_access = work.get("open_access", {})
                        if open_access and isinstance(open_access, dict):
                            metadata.oa_url = open_access.get("oa_url")
                        
                        # Extract primary topic
                        primary_topic = work.get("primary_topic")
                        if primary_topic and isinstance(primary_topic, dict):
                            metadata.primary_topic = primary_topic
                        
                        metadata.openalex_retrieved = True
                        enriched.append(metadata)
                
                # Add papers that weren't found in OpenAlex
                found_dois = {work.get('doi', '').replace('https://doi.org/', '').lower() for work in results}
                for doi in batch_dois:
                    if doi.lower() not in found_dois:
                        enriched.append(doi_to_metadata[doi.lower()])
                        
            elif response.status_code == 429:
                print(f"⚠ OpenAlex rate limit (429) during batch fetch, falling back to individual requests...")
                # Fallback to individual requests for this batch
                for doi in batch_dois:
                    metadata = doi_to_metadata[doi.lower()]
                    enriched.append(enrich_with_openalex(metadata))
            else:
                print(f"⚠ OpenAlex batch request failed ({response.status_code}), falling back to individual requests...")
                for doi in batch_dois:
                    metadata = doi_to_metadata[doi.lower()]
                    enriched.append(enrich_with_openalex(metadata))
                    
        except Exception as e:
            print(f"⚠ Error in batch OpenAlex request: {e}, falling back to individual requests...")
            for doi in batch_dois:
                metadata = doi_to_metadata[doi.lower()]
                enriched.append(enrich_with_openalex(metadata))
    
    # Add papers without DOIs
    enriched.extend(papers_without_doi)
    
    return enriched
