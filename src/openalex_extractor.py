#!/usr/bin/env python3
"""
OpenAlex metadata extractor
"""
import time
import requests
from typing import Optional

from .models import PaperMetadata
from .config import OPENALEX_DELAY, MAX_RETRIES, RETRY_DELAY


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
    
    url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(OPENALEX_DELAY)  # Rate limiting
            response = requests.get(url, timeout=10)
            
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
                    
                    # Debug log topic fields
                    topic_name = primary_topic.get('display_name')
                    topic_subfield = primary_topic.get('subfield', {}).get('display_name') if 'subfield' in primary_topic else None
                    topic_field = primary_topic.get('field', {}).get('display_name') if 'field' in primary_topic else None
                    topic_domain = primary_topic.get('domain', {}).get('display_name') if 'domain' in primary_topic else None
                    
                    print(f"Topic info for {metadata.doi}:")
                    print(f"  - Topic: {topic_name}")
                    print(f"  - Subfield: {topic_subfield}")
                    print(f"  - Field: {topic_field}")
                    print(f"  - Domain: {topic_domain}")
                
                metadata.openalex_retrieved = True
                return metadata
                
            elif response.status_code == 404:
                # DOI not found in OpenAlex
                return metadata
            else:
                if attempt < MAX_RETRIES - 1:
                    print(f"OpenAlex API returned {response.status_code} for DOI {doi}, retrying...")
                    time.sleep(RETRY_DELAY)
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


def batch_enrich_with_openalex(metadata_list: list[PaperMetadata]) -> list[PaperMetadata]:
    """
    Enrich multiple papers with OpenAlex data.
    
    Args:
        metadata_list: List of PaperMetadata objects
        
    Returns:
        List of enriched PaperMetadata objects
    """
    enriched = []
    for metadata in metadata_list:
        enriched.append(enrich_with_openalex(metadata))
    return enriched
