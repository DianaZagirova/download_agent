#!/usr/bin/env python3
"""
Query cache for storing PubMed search results
Avoids re-fetching PMIDs for identical queries
"""
import json
import hashlib
import os
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from .config import BASE_DIR


class QueryCache:
    """Cache for PubMed query results (PMIDs)"""
    
    def __init__(self, cache_dir: str = None):
        """Initialize query cache"""
        if cache_dir is None:
            cache_dir = os.path.join(BASE_DIR, 'cache')
        
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.cache_file = os.path.join(cache_dir, 'query_cache.json')
        self._load_cache()
    
    def _load_cache(self):
        """Load cache from disk"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load cache: {e}")
                self.cache = {}
        else:
            self.cache = {}
    
    def _save_cache(self):
        """Save cache to disk"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")
    
    def _get_query_hash(self, query: str) -> str:
        """Generate hash for query to use as cache key"""
        # Normalize query (remove extra whitespace)
        normalized = ' '.join(query.split())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def get(self, query: str) -> Optional[List[str]]:
        """
        Get cached PMIDs for a query
        
        Args:
            query: PubMed query string
            
        Returns:
            List of PMIDs if cached, None otherwise
        """
        query_hash = self._get_query_hash(query)
        
        if query_hash in self.cache:
            cache_entry = self.cache[query_hash]
            pmids = cache_entry.get('pmids', [])
            cached_date = cache_entry.get('cached_date', 'unknown')
            count = len(pmids)
            
            print(f"✓ Found cached results: {count:,} PMIDs")
            print(f"  Cached on: {cached_date}")
            print(f"  Query hash: {query_hash[:16]}...")
            
            return pmids
        
        return None
    
    def set(self, query: str, pmids: List[str]):
        """
        Cache PMIDs for a query
        
        Args:
            query: PubMed query string
            pmids: List of PMIDs
        """
        query_hash = self._get_query_hash(query)
        
        self.cache[query_hash] = {
            'query': query[:200] + ('...' if len(query) > 200 else ''),  # Truncate long queries
            'pmids': pmids,
            'count': len(pmids),
            'cached_date': datetime.now().isoformat()
        }
        
        self._save_cache()
        
        print(f"✓ Cached {len(pmids):,} PMIDs for future use")
        print(f"  Cache file: {self.cache_file}")
    
    def clear(self):
        """Clear all cached queries"""
        self.cache = {}
        self._save_cache()
        print("✓ Cache cleared")
    
    def get_cache_info(self) -> dict:
        """Get information about the cache"""
        total_queries = len(self.cache)
        total_pmids = sum(entry.get('count', 0) for entry in self.cache.values())
        
        # Get cache file size
        cache_size = 0
        if os.path.exists(self.cache_file):
            cache_size = os.path.getsize(self.cache_file)
        
        return {
            'total_queries': total_queries,
            'total_pmids': total_pmids,
            'cache_file': self.cache_file,
            'cache_size_bytes': cache_size,
            'cache_size_kb': cache_size / 1024
        }
    
    def list_cached_queries(self):
        """Print all cached queries"""
        if not self.cache:
            print("No queries cached")
            return
        
        print(f"\nCached Queries ({len(self.cache)} total):")
        print("=" * 80)
        
        for query_hash, entry in self.cache.items():
            query_text = entry.get('query', 'N/A')
            count = entry.get('count', 0)
            cached_date = entry.get('cached_date', 'unknown')
            
            print(f"Hash: {query_hash[:16]}...")
            print(f"  Query: {query_text}")
            print(f"  PMIDs: {count:,}")
            print(f"  Cached: {cached_date}")
            print()
