#!/usr/bin/env python3
"""
Example usage of the PubMed paper collection system
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import collect_papers
from src.database import PaperDatabase


def example_1_basic_collection():
    """Example 1: Basic paper collection with a simple query"""
    query = """
    (
      (
        aging[Title] OR ageing[Title] 
      )
      AND
      (
        theory[Title] OR theories[Title] OR hypothesis[Title] OR hypotheses[Title] OR paradigm[Title] OR paradigms[Title]
      )
      OR ("theory of aging"[TI] OR "theory of ageing")
    )
    NOT
    (
      Case Reports[Publication Type] OR "case report"[Title] OR "case reports"[Title] OR Clinical Trial[Publication Type] OR "protocol"[Title] OR "conference"[Title] OR "meeting"[Title] OR "healthy aging"[TI] OR "healthy ageing"[TI] OR "well-being"[TI] OR "successful aging"[TI] OR "successful ageing"[TI] OR "normal ageing"[TI] OR "normal aging"[TI] OR "ovarian"[TI] OR "liver"[TI] OR "kidne*"[TI] OR "skin"[TI] OR "religion"[TI] OR "enjoyment"[TI] OR "disease hypothesis"[TI] OR "biological aging"[TI] OR "biological ageing"[TI] 
    )
    """
    
    # Collect papers (limit to 100 for testing)
    collect_papers(query, max_results=100, use_threading=True)


def example_2_database_queries():
    """Example 2: Query the database after collection"""
    db = PaperDatabase()
    
    # Get statistics
    stats = db.get_statistics()
    print("\nDatabase Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Get papers with full text
    papers_with_fulltext = db.get_papers_with_fulltext()
    print(f"\nPapers with full text: {len(papers_with_fulltext)}")
    
    # Print first 5 papers
    print("\nFirst 5 papers with full text:")
    for i, paper in enumerate(papers_with_fulltext[:5], 1):
        print(f"\n{i}. {paper.title}")
        print(f"   PMID: {paper.pmid} | DOI: {paper.doi}")
        print(f"   Journal: {paper.journal} ({paper.year})")
        print(f"   Citations: {paper.cited_by_count}")
        print(f"   Full text length: {len(paper.full_text) if paper.full_text else 0} characters")
    
    # Get papers without full text
    papers_without_fulltext = db.get_papers_without_fulltext()
    print(f"\n\nPapers without full text: {len(papers_without_fulltext)}")
    
    # Export to JSON
    json_path = db.export_to_json("my_custom_export.json")
    print(f"\nExported all papers to: {json_path}")
    
    db.close()


def example_3_custom_query():
    """Example 3: Use a completely different query"""
    # Query for machine learning papers in medicine
    query = """
    (
      ("machine learning"[Title/Abstract] OR "deep learning"[Title/Abstract] OR "artificial intelligence"[Title/Abstract])
      AND
      ("medicine"[MeSH Terms] OR "clinical"[Title/Abstract])
    )
    AND
    (
      2020:2024[pdat]
    )
    NOT
    (
      Review[Publication Type]
    )
    """
    
    # Collect papers
    collect_papers(query, max_results=500, use_threading=True)


def example_4_analyze_specific_paper():
    """Example 4: Analyze a specific paper by PMID"""
    from src.pubmed_extractor import process_paper
    from src.openalex_extractor import enrich_with_openalex
    
    # Process a specific PMID
    pmid = "12345678"  # Replace with actual PMID
    
    print(f"Processing paper PMID: {pmid}")
    metadata = process_paper(pmid)
    
    if metadata:
        print(f"\nTitle: {metadata.title}")
        print(f"Authors: {', '.join(metadata.authors[:3])}...")
        print(f"Journal: {metadata.journal} ({metadata.year})")
        print(f"Has full text: {metadata.is_full_text_pmc}")
        
        if metadata.doi:
            print(f"\nEnriching with OpenAlex data...")
            metadata = enrich_with_openalex(metadata)
            print(f"Citations: {metadata.cited_by_count}")
            print(f"FWCI: {metadata.fwci}")
            print(f"Topic: {metadata.primary_topic}")
    else:
        print("Failed to retrieve paper metadata")


if __name__ == "__main__":
    # Run the example you want
    print("Choose an example to run:")
    print("1. Basic paper collection (100 papers)")
    print("2. Query existing database")
    print("3. Custom query (ML in medicine)")
    print("4. Analyze specific paper")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        example_1_basic_collection()
    elif choice == "2":
        example_2_database_queries()
    elif choice == "3":
        example_3_custom_query()
    elif choice == "4":
        example_4_analyze_specific_paper()
    else:
        print("Invalid choice. Running example 1...")
        example_1_basic_collection()
