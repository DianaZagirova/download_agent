#!/usr/bin/env python3
"""
Utility script to convert failed_dois.txt to structured JSON format
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import PaperDatabase


def convert_to_json(db_path: str = None):
    """
    Convert failed DOIs from database to structured JSON format.
    
    Args:
        db_path: Path to database file (uses default if None)
    """
    print("Opening database...")
    if db_path:
        db = PaperDatabase(db_path)
    else:
        db = PaperDatabase()
    
    # Get papers without full text
    papers = db.get_papers_without_fulltext()
    print(f"Found {len(papers)} papers without PMC full text")
    
    if not papers:
        print("No papers without full text found!")
        db.close()
        return
    
    # Export to JSON
    print("\nExporting to JSON format...")
    json_path = db.export_failed_dois_to_file(format='json')
    
    print(f"\n✅ Successfully exported to: {json_path}")
    print("\nJSON structure:")
    print("  {")
    print("    'total_count': <number>,")
    print("    'papers': [")
    print("      {")
    print("        'pmid': <pmid>,")
    print("        'doi': <doi>,")
    print("        'title': <title>,")
    print("        'journal': <journal>,")
    print("        'year': <year>,")
    print("        'authors': [<first 3 authors>],")
    print("        'abstract': <first 200 chars>,")
    print("        'oa_url': <open access url>,")
    print("        'collection_date': <date>")
    print("      },")
    print("      ...")
    print("    ]")
    print("  }")
    
    # Also export TXT for backward compatibility
    print("\nExporting TXT format for backward compatibility...")
    txt_path = db.export_failed_dois_to_file(format='txt')
    print(f"✅ TXT format exported to: {txt_path}")
    
    db.close()


if __name__ == "__main__":
    print("="*60)
    print("CONVERT FAILED DOIs TO JSON")
    print("="*60)
    print()
    
    convert_to_json()
