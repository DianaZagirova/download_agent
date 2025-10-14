#!/usr/bin/env python3
"""
Utility to manage the PubMed query cache
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.query_cache import QueryCache

def main():
    cache = QueryCache()
    
    if len(sys.argv) < 2:
        print("Usage: python scripts/manage_cache.py [command]")
        print("\nCommands:")
        print("  info    - Show cache information")
        print("  list    - List all cached queries")
        print("  clear   - Clear all cached queries")
        print("  stats   - Show cache statistics")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "info" or command == "stats":
        info = cache.get_cache_info()
        print("\n" + "="*80)
        print("CACHE INFORMATION")
        print("="*80)
        print(f"Cache file: {info['cache_file']}")
        print(f"Total cached queries: {info['total_queries']}")
        print(f"Total PMIDs cached: {info['total_pmids']:,}")
        print(f"Cache size: {info['cache_size_kb']:.2f} KB ({info['cache_size_bytes']:,} bytes)")
        print("="*80)
        
    elif command == "list":
        cache.list_cached_queries()
        
    elif command == "clear":
        confirm = input("Are you sure you want to clear the cache? (yes/no): ")
        if confirm.lower() == "yes":
            cache.clear()
            print("✓ Cache cleared successfully")
        else:
            print("Cache clear cancelled")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
