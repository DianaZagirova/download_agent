#!/usr/bin/env python3
"""
Find papers that are missing full_text OR abstract
"""
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import PaperDatabase
from src.config import DATABASE_PATH


def find_papers_missing_content():
    """Find all papers missing full_text or abstract"""
    
    with PaperDatabase(DATABASE_PATH) as db:
        # Get all papers
        all_papers = db.get_all_papers()
        
        missing_content_papers = []
        
        for paper in all_papers:
            # Check if abstract is missing or empty
            has_abstract = paper.abstract and len(paper.abstract.strip()) > 0
            
            # Check if full_text is missing (using the has_full_text method)
            has_full_text = paper.has_full_text()
            
            # If missing either abstract OR full_text
            if not has_abstract or not has_full_text:
                identifier = paper.doi if paper.doi else paper.title
                missing_content_papers.append({
                    'identifier': identifier,
                    'doi': paper.doi,
                    'title': paper.title,
                    'pmid': paper.pmid,
                    'has_abstract': has_abstract,
                    'has_full_text': has_full_text
                })
        
        # Print results
        print(f"Total papers in database: {len(all_papers)}")
        print(f"Papers missing full_text OR abstract: {len(missing_content_papers)}\n")
        print("=" * 80)
        
        for paper_info in missing_content_papers:
            print(f"{paper_info['identifier']}")
            print(f"  PMID: {paper_info['pmid']}")
            print(f"  Has abstract: {paper_info['has_abstract']}")
            print(f"  Has full_text: {paper_info['has_full_text']}")
            print("-" * 80)
        
        # Also save to a file
        output_file = Path(DATABASE_PATH).parent / "papers_missing_content.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# Papers missing full_text OR abstract\n")
            f.write(f"# Total: {len(missing_content_papers)}\n")
            f.write("# Format: DOI or Title\n\n")
            for paper_info in missing_content_papers:
                f.write(f"{paper_info['identifier']}\n")
        
        print(f"\nResults also saved to: {output_file}")
        
        return missing_content_papers


if __name__ == "__main__":
    find_papers_missing_content()
