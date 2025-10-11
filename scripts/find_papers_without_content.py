#!/usr/bin/env python3
"""
Script to find papers with no abstract OR no full text
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import PaperDatabase
from src.config import DATABASE_PATH
import json


def find_papers_without_content(db_path: str = None, export_format: str = 'json'):
    """
    Find papers that have no abstract OR no full text.
    
    Args:
        db_path: Path to database (optional)
        export_format: Output format ('json', 'csv', or 'txt')
    """
    print("="*60)
    print("PAPERS WITHOUT ABSTRACT OR FULL TEXT")
    print("="*60)
    
    # Initialize database
    if db_path:
        db = PaperDatabase(db_path=db_path)
    else:
        db = PaperDatabase()
    
    print(f"\nDatabase: {db.db_path}\n")
    
    cursor = db.conn.cursor()
    
    # Query for papers without abstract OR full text
    query = """
        SELECT 
            pmid,
            pmcid,
            doi,
            title,
            abstract,
            full_text,
            year,
            journal,
            authors,
            is_full_text_pmc
        FROM papers
        WHERE 
            (abstract IS NULL OR abstract = '' OR abstract = 'None')
            OR 
            (full_text IS NULL OR full_text = '' OR full_text = 'None')
        ORDER BY year DESC, pmid
    """
    
    cursor.execute(query)
    papers = cursor.fetchall()
    
    print(f"Found {len(papers)} papers without abstract or full text\n")
    
    # Categorize papers
    no_abstract = []
    no_fulltext = []
    no_both = []
    
    for paper in papers:
        has_abstract = paper['abstract'] and paper['abstract'] not in ['', 'None']
        has_fulltext = paper['full_text'] and paper['full_text'] not in ['', 'None']
        
        if not has_abstract and not has_fulltext:
            no_both.append(paper)
        elif not has_abstract:
            no_abstract.append(paper)
        elif not has_fulltext:
            no_fulltext.append(paper)
    
    # Print statistics
    print("BREAKDOWN:")
    print(f"  - No abstract only: {len(no_abstract)} papers")
    print(f"  - No full text only: {len(no_fulltext)} papers")
    print(f"  - No abstract AND no full text: {len(no_both)} papers")
    print(f"  - Total: {len(papers)} papers")
    
    # Show examples
    if no_both:
        print(f"\n{'='*60}")
        print("PAPERS WITH NO ABSTRACT AND NO FULL TEXT (first 5)")
        print(f"{'='*60}")
        for paper in no_both[:5]:
            print(f"\nPMID: {paper['pmid']}")
            print(f"  Title: {paper['title'][:80] if paper['title'] else 'N/A'}...")
            print(f"  Year: {paper['year'] if paper['year'] else 'N/A'}")
            print(f"  DOI: {paper['doi'] if paper['doi'] else 'N/A'}")
            print(f"  Journal: {paper['journal'][:50] if paper['journal'] else 'N/A'}")
            print(f"  URL: https://pubmed.ncbi.nlm.nih.gov/{paper['pmid']}/")
    
    # Export results
    output_dir = os.path.dirname(db.db_path)
    
    if export_format == 'json':
        output_file = os.path.join(output_dir, 'papers_without_content.json')
        
        export_data = {
            'summary': {
                'total': len(papers),
                'no_abstract_only': len(no_abstract),
                'no_fulltext_only': len(no_fulltext),
                'no_both': len(no_both)
            },
            'papers': {
                'no_abstract_only': [dict(p) for p in no_abstract],
                'no_fulltext_only': [dict(p) for p in no_fulltext],
                'no_both': [dict(p) for p in no_both]
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Exported to JSON: {output_file}")
    
    elif export_format == 'csv':
        import csv
        output_file = os.path.join(output_dir, 'papers_without_content.csv')
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['PMID', 'Title', 'Year', 'DOI', 'Journal', 'Has Abstract', 'Has Full Text', 'URL'])
            
            for paper in papers:
                has_abstract = paper['abstract'] and paper['abstract'] not in ['', 'None']
                has_fulltext = paper['full_text'] and paper['full_text'] not in ['', 'None']
                
                writer.writerow([
                    paper['pmid'],
                    paper['title'] if paper['title'] else '',
                    paper['year'] if paper['year'] else '',
                    paper['doi'] if paper['doi'] else '',
                    paper['journal'] if paper['journal'] else '',
                    'Yes' if has_abstract else 'No',
                    'Yes' if has_fulltext else 'No',
                    f"https://pubmed.ncbi.nlm.nih.gov/{paper['pmid']}/"
                ])
        
        print(f"\n✓ Exported to CSV: {output_file}")
    
    elif export_format == 'txt':
        output_file = os.path.join(output_dir, 'papers_without_content.txt')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("PAPERS WITHOUT ABSTRACT OR FULL TEXT\n")
            f.write("="*60 + "\n\n")
            
            f.write(f"Total: {len(papers)} papers\n")
            f.write(f"  - No abstract only: {len(no_abstract)}\n")
            f.write(f"  - No full text only: {len(no_fulltext)}\n")
            f.write(f"  - No both: {len(no_both)}\n\n")
            
            f.write("="*60 + "\n")
            f.write("NO ABSTRACT AND NO FULL TEXT\n")
            f.write("="*60 + "\n\n")
            
            for paper in no_both:
                f.write(f"PMID: {paper['pmid']}\n")
                f.write(f"Title: {paper['title']}\n")
                f.write(f"Year: {paper['year']}\n")
                f.write(f"DOI: {paper['doi']}\n")
                f.write(f"Journal: {paper['journal']}\n")
                f.write(f"URL: https://pubmed.ncbi.nlm.nih.gov/{paper['pmid']}/\n")
                f.write("\n")
            
            f.write("="*60 + "\n")
            f.write("NO ABSTRACT ONLY\n")
            f.write("="*60 + "\n\n")
            
            for paper in no_abstract:
                f.write(f"PMID: {paper['pmid']}\n")
                f.write(f"Title: {paper['title']}\n")
                f.write(f"Year: {paper['year']}\n")
                f.write(f"URL: https://pubmed.ncbi.nlm.nih.gov/{paper['pmid']}/\n")
                f.write("\n")
            
            f.write("="*60 + "\n")
            f.write("NO FULL TEXT ONLY\n")
            f.write("="*60 + "\n\n")
            
            for paper in no_fulltext:
                f.write(f"PMID: {paper['pmid']}\n")
                f.write(f"Title: {paper['title']}\n")
                f.write(f"Year: {paper['year']}\n")
                f.write(f"URL: https://pubmed.ncbi.nlm.nih.gov/{paper['pmid']}/\n")
                f.write("\n")
        
        print(f"\n✓ Exported to TXT: {output_file}")
    
    # Also create a simple PMID list for easy reprocessing
    pmid_list_file = os.path.join(output_dir, 'papers_without_content_pmids.txt')
    with open(pmid_list_file, 'w') as f:
        for paper in papers:
            f.write(f"{paper['pmid']}\n")
    
    print(f"✓ PMID list saved: {pmid_list_file}")
    
    db.close()
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Find papers with no abstract or full text',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default database, export as JSON
  python scripts/find_papers_without_content.py
  
  # Use custom database
  python scripts/find_papers_without_content.py --db paper_collection_test/data/papers.db
  
  # Export as CSV
  python scripts/find_papers_without_content.py --format csv
  
  # Export as TXT
  python scripts/find_papers_without_content.py --format txt
        """
    )
    
    parser.add_argument('--db', type=str, help='Path to database file', default=None)
    parser.add_argument('--format', type=str, choices=['json', 'csv', 'txt'], 
                       default='json', help='Export format (default: json)')
    
    args = parser.parse_args()
    
    find_papers_without_content(db_path=args.db, export_format=args.format)
