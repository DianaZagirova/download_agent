#!/usr/bin/env python3
"""
Quick reference examples for querying papers by query_id and MeSH terms
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent / "paper_collection" / "data"))

from example_queries import (
    get_papers_by_query_id,
    get_dois_by_query_and_mesh,
    get_dois_by_mesh_term
)


def example_1_show_queries():
    """Show all available queries"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Show all queries")
    print("="*70)
    
    get_papers_by_query_id()


def example_2_get_female_dois():
    """Get DOIs for papers with 'Female' MeSH term from query 1"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Get DOIs with 'Female' MeSH term from Query 1")
    print("="*70)
    
    dois = get_dois_by_query_and_mesh(query_id=1, mesh_term="Female")
    
    # Save to file
    output_file = "female_papers_dois.txt"
    with open(output_file, 'w') as f:
        for doi in dois:
            f.write(f"{doi}\n")
    
    print(f"\n✓ Saved {len(dois)} DOIs to {output_file}")


def example_3_get_male_dois():
    """Get DOIs for papers with 'Male' MeSH term from query 1"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Get DOIs with 'Male' MeSH term from Query 1")
    print("="*70)
    
    dois = get_dois_by_query_and_mesh(query_id=1, mesh_term="Male")
    
    output_file = "male_papers_dois.txt"
    with open(output_file, 'w') as f:
        for doi in dois:
            f.write(f"{doi}\n")
    
    print(f"\n✓ Saved {len(dois)} DOIs to {output_file}")


def example_4_all_query_1_dois():
    """Get all DOIs from query 1"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Get all DOIs from Query 1")
    print("="*70)
    
    result = get_papers_by_query_id(query_id=1)
    dois = result['dois']
    
    output_file = "all_query1_dois.txt"
    with open(output_file, 'w') as f:
        for doi in dois:
            f.write(f"{doi}\n")
    
    print(f"\n✓ Saved {len(dois)} DOIs to {output_file}")


def example_5_aging_mesh_dois():
    """Get DOIs for papers with 'Aging' MeSH term (any query)"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Get DOIs with 'Aging' MeSH term (any query)")
    print("="*70)
    
    dois = get_dois_by_mesh_term("Aging")
    
    output_file = "aging_mesh_dois.txt"
    with open(output_file, 'w') as f:
        for doi in dois:
            f.write(f"{doi}\n")
    
    print(f"\n✓ Saved {len(dois)} DOIs to {output_file}")


def example_6_custom_sql():
    """Custom SQL query example"""
    print("\n" + "="*70)
    print("EXAMPLE 6: Custom SQL - Female + High Citations")
    print("="*70)
    
    import sqlite3
    import json
    
    db_path = Path(__file__).parent / "paper_collection" / "data" / "papers.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get papers from query 1 with "Female" MeSH term and >50 citations
    cursor.execute("""
        SELECT doi, pmid, title, mesh_terms, cited_by_count, year
        FROM papers
        WHERE query_id = 1 
        AND mesh_terms IS NOT NULL
        AND cited_by_count > 50
    """)
    
    results = []
    for row in cursor.fetchall():
        if row['mesh_terms']:
            mesh_terms = json.loads(row['mesh_terms'])
            if "Female" in mesh_terms and row['doi']:
                results.append({
                    'doi': row['doi'],
                    'pmid': row['pmid'],
                    'title': row['title'],
                    'citations': row['cited_by_count'],
                    'year': row['year']
                })
    
    conn.close()
    
    print(f"\nFound {len(results)} highly cited papers with 'Female' MeSH term:")
    for i, paper in enumerate(results[:10], 1):
        print(f"  {i}. [{paper['citations']} cites] {paper['title'][:60]}...")
        print(f"     DOI: {paper['doi']}")
    
    if len(results) > 10:
        print(f"  ... and {len(results) - 10} more")
    
    # Save DOIs
    output_file = "female_highly_cited_dois.txt"
    with open(output_file, 'w') as f:
        for paper in results:
            f.write(f"{paper['doi']}\n")
    
    print(f"\n✓ Saved {len(results)} DOIs to {output_file}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Quick query examples")
    parser.add_argument("--example", type=int, choices=[1,2,3,4,5,6], 
                       help="Run specific example (1-6)")
    parser.add_argument("--all", action="store_true", 
                       help="Run all examples")
    
    args = parser.parse_args()
    
    if args.all:
        example_1_show_queries()
        example_2_get_female_dois()
        example_3_get_male_dois()
        example_4_all_query_1_dois()
        example_5_aging_mesh_dois()
        example_6_custom_sql()
    elif args.example:
        {
            1: example_1_show_queries,
            2: example_2_get_female_dois,
            3: example_3_get_male_dois,
            4: example_4_all_query_1_dois,
            5: example_5_aging_mesh_dois,
            6: example_6_custom_sql
        }[args.example]()
    else:
        print("Usage examples:")
        print("  python quick_query_examples.py --example 1  # Show all queries")
        print("  python quick_query_examples.py --example 2  # Get Female DOIs")
        print("  python quick_query_examples.py --example 3  # Get Male DOIs")
        print("  python quick_query_examples.py --all        # Run all examples")
        print("\nAvailable examples:")
        print("  1. Show all queries")
        print("  2. Get DOIs with 'Female' MeSH term from Query 1")
        print("  3. Get DOIs with 'Male' MeSH term from Query 1")
        print("  4. Get all DOIs from Query 1")
        print("  5. Get DOIs with 'Aging' MeSH term (any query)")
        print("  6. Custom SQL - Female + High Citations")
