#!/usr/bin/env python3
"""
Utility script to re-clean existing papers in the database
Useful if you already collected papers and want to apply text cleaning
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import PaperDatabase
from src.text_cleaner import clean_text_comprehensive, clean_abstract
from tqdm import tqdm


def reclean_all_papers(db_path: str = None):
    """
    Re-clean all papers in the database.
    
    Args:
        db_path: Path to database file (uses default if None)
    """
    print("Opening database...")
    if db_path:
        db = PaperDatabase(db_path)
    else:
        db = PaperDatabase()
    
    # Get all papers
    papers = db.get_all_papers()
    print(f"Found {len(papers)} papers in database")
    
    if not papers:
        print("No papers to clean!")
        db.close()
        return
    
    # Ask for confirmation
    response = input(f"\nThis will re-clean {len(papers)} papers. Continue? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        db.close()
        return
    
    print("\nRe-cleaning papers...")
    cleaned_count = 0
    
    for paper in tqdm(papers, desc="Cleaning papers"):
        modified = False
        
        # Clean abstract
        if paper.abstract:
            cleaned_abstract = clean_abstract(paper.abstract)
            if cleaned_abstract != paper.abstract:
                paper.abstract = cleaned_abstract
                modified = True
        
        # Clean full text
        if paper.full_text:
            cleaned_fulltext = clean_text_comprehensive(paper.full_text, remove_references=True)
            if cleaned_fulltext != paper.full_text:
                paper.full_text = cleaned_fulltext
                modified = True
        
        # Update in database if modified
        if modified:
            db.insert_paper(paper)
            cleaned_count += 1
    
    print(f"\nCleaning completed!")
    print(f"  - Total papers: {len(papers)}")
    print(f"  - Papers modified: {cleaned_count}")
    print(f"  - Papers unchanged: {len(papers) - cleaned_count}")
    
    # Export cleaned data
    print("\nExporting cleaned data...")
    json_path = db.export_to_json()
    print(f"Exported to: {json_path}")
    
    db.close()


def preview_cleaning_effect(db_path: str = None, num_samples: int = 3):
    """
    Preview the effect of cleaning on a few sample papers.
    
    Args:
        db_path: Path to database file (uses default if None)
        num_samples: Number of papers to preview
    """
    print("Opening database...")
    if db_path:
        db = PaperDatabase(db_path)
    else:
        db = PaperDatabase()
    
    # Get papers with full text
    papers = db.get_papers_with_fulltext()[:num_samples]
    
    if not papers:
        print("No papers with full text found!")
        db.close()
        return
    
    print(f"\nPreviewing cleaning effect on {len(papers)} papers:\n")
    
    for i, paper in enumerate(papers, 1):
        print("="*60)
        print(f"Paper {i}: {paper.title[:60]}...")
        print("="*60)
        
        if paper.full_text:
            original = paper.full_text[:500]
            cleaned = clean_text_comprehensive(paper.full_text, remove_references=True)[:500]
            
            print("\nORIGINAL (first 500 chars):")
            print(original)
            print("\nCLEANED (first 500 chars):")
            print(cleaned)
            print("\n")
    
    db.close()


if __name__ == "__main__":
    import sys
    
    print("="*60)
    print("DATABASE TEXT CLEANING UTILITY")
    print("="*60)
    print("\nOptions:")
    print("1. Preview cleaning effect (3 sample papers)")
    print("2. Re-clean all papers in database")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        preview_cleaning_effect()
    elif choice == "2":
        reclean_all_papers()
    elif choice == "3":
        print("Exiting...")
    else:
        print("Invalid choice!")
