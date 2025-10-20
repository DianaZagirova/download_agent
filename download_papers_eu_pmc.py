#!/usr/bin/env python3
"""
Collect all papers related to aging theories from Europe PMC
Includes published papers and preprints
"""

from scripts.download_europepmc import collect_europepmc_papers

# Query strategies for comprehensive aging theories coverage
AGING_THEORIES_QUERIES = {
    
    # Option 1: Comprehensive query (RECOMMENDED)
    "comprehensive": """
        (aging OR ageing OR senescence OR longevity) AND 
        (theory OR theories OR hypothesis OR hypotheses OR mechanism OR mechanisms OR 
         "hallmarks of aging" OR "aging hallmarks" OR 
         "damage accumulation" OR "disposable soma" OR 
         "antagonistic pleiotropy" OR "mutation accumulation" OR
         "programmed aging" OR "hyperfunction" OR 
         "genomic instability" OR "telomere attrition" OR 
         "epigenetic alterations" OR "proteostasis" OR 
         "mitochondrial dysfunction" OR "cellular senescence" OR 
         "stem cell exhaustion" OR "altered intercellular communication" OR
         "inflammaging" OR "immunosenescence")
    """,
    
    # Option 2: Specific aging theories (focused)
    "specific_theories": """
    ("theory of aging" OR "aging theory" OR "ageing theory" OR "theories of aging" OR "theory of ageing" OR "theories of ageing") OR
        ("damage accumulation theory" OR "disposable soma theory" OR 
         "antagonistic pleiotropy" OR "mutation accumulation theory" OR
         "free radical theory" OR "oxidative stress theory" OR
         "programmed aging" OR "hyperfunction theory" OR
         "hallmarks of aging" OR "pillars of aging")
    """,
    
    # Option 3: Molecular mechanisms
    "molecular_mechanisms": """
        (aging OR ageing) AND
        ("genomic instability" OR "telomere shortening" OR "DNA damage" OR
         "epigenetic changes" OR "histone modifications" OR "DNA methylation" OR
         "protein misfolding" OR "proteostasis loss" OR "autophagy" OR
         "mitochondrial dysfunction" OR "mitophagy" OR "reactive oxygen species" OR
         "cellular senescence" OR "SASP" OR "senescence-associated secretory phenotype" OR
         "stem cell dysfunction" OR "tissue regeneration" OR
         "inflammation" OR "inflammaging" OR "immune aging")
    """,
    
    # Option 4: Evolutionary theories
    "evolutionary": """
        (aging OR ageing OR senescence) AND
        ("evolutionary theory" OR "evolution" OR 
         "antagonistic pleiotropy" OR "mutation accumulation" OR
         "life history theory" OR "trade-offs" OR
         "disposable soma" OR "investment" OR
         "reproduction" OR "fitness" OR "selection")
    """,
    
    # Option 5: Recent comprehensive (2020+)
    "recent_comprehensive": """
        (aging OR ageing OR senescence OR longevity) AND 
        (theory OR theories OR hypothesis OR mechanism OR 
         "hallmarks" OR "molecular basis" OR "mechanisms") AND
        PUB_YEAR:[2020 TO 2025]
    """
}

AGING_THEORIES_QUERIES = {"combined_pmc":
 """
(
  (TITLE:"theory of aging" OR ABSTRACT:"theory of aging") OR
  (TITLE:"aging theory" OR ABSTRACT:"aging theory") OR
  (TITLE:"ageing theory" OR ABSTRACT:"ageing theory") OR
  (TITLE:"theories of aging" OR ABSTRACT:"theories of aging") OR
  (TITLE:"theory of ageing" OR ABSTRACT:"theory of ageing") OR
  (TITLE:"theories of ageing" OR ABSTRACT:"theories of ageing") OR
  ("disposable soma theory" ) OR
  ("mutation accumulation theory") OR
  ("free radical theory") OR
  ("oxidative stress theory" ) OR
  (TITLE:"hallmarks of aging" OR ABSTRACT:"hallmarks of aging") OR
  (TITLE:"pillars of aging" OR ABSTRACT:"pillars of aging")
)"""}

def collect_all_aging_theories(max_results_per_query=10000, include_preprints=True):
    """
    Collect papers on aging theories using multiple query strategies
    
    Args:
        max_results_per_query: Maximum papers per query (default: 10000)
        include_preprints: Include preprints (default: True)
    """
    
    print("="*80)
    print("AGING THEORIES - COMPREHENSIVE LITERATURE COLLECTION")
    print("="*80)
    print(f"\nStrategy: Multiple targeted queries")
    print(f"Max results per query: {max_results_per_query:,}")
    print(f"Include preprints: {include_preprints}")
    print("="*80 + "\n")
    
    print("\n" + "="*80)
    print("QUERY 1: COMPREHENSIVE AGING THEORIES")
    print("="*80)
    
    collect_europepmc_papers(
        query=AGING_THEORIES_QUERIES["combined_pmc"],
        max_results=max_results_per_query,
        include_preprints=include_preprints,
        use_threading=True,
        output_dir=None,  # Use default paper_collection directory
        query_description="Comprehensive aging theories"
    )
    
    print("\n✅ Comprehensive query complete!")
    print("="*80)


def collect_by_specific_category(category="comprehensive", 
                                  max_results=10000, 
                                  include_preprints=True):
    """
    Collect papers for a specific category
    
    Args:
        category: One of: comprehensive, specific_theories, molecular_mechanisms, 
                  evolutionary, recent_comprehensive
        max_results: Maximum number of papers
        include_preprints: Include preprints
    """
    
    if category not in AGING_THEORIES_QUERIES:
        print(f"❌ Unknown category: {category}")
        print(f"Available categories: {', '.join(AGING_THEORIES_QUERIES.keys())}")
        return
    
    print(f"\n{'='*80}")
    print(f"COLLECTING: {category.upper().replace('_', ' ')}")
    print(f"{'='*80}")
    
    collect_europepmc_papers(
        query=AGING_THEORIES_QUERIES[category],
        max_results=max_results,
        include_preprints=include_preprints,
        use_threading=True,
        output_dir=f"aging_theories_{category}",
        query_description=f"Aging theories - {category}"
    )


def main():
    """Main execution"""
    
    # OPTION A: Comprehensive collection (RECOMMENDED START)
    # This will get you the most papers with a single query
    collect_all_aging_theories(
        max_results_per_query=50000,  # Comprehensive collection
        include_preprints=True
    )
    
    # OPTION B: Specific category only
    # Uncomment the category you want:
    
    # collect_by_specific_category("comprehensive", max_results=50000)
    # collect_by_specific_category("specific_theories", max_results=10000)
    # collect_by_specific_category("molecular_mechanisms", max_results=20000)
    # collect_by_specific_category("evolutionary", max_results=5000)
    # collect_by_specific_category("recent_comprehensive", max_results=10000)
    
    
    # OPTION C: Multiple targeted queries (for complete coverage)
    # Uncomment to run all queries:
    
    # for category in AGING_THEORIES_QUERIES.keys():
    #     collect_by_specific_category(category, max_results=10000)
    
    
    print("\n" + "="*80)
    print("COLLECTION COMPLETE!")
    print("="*80)
    
    # Show statistics
    from src.database import PaperDatabase
    import sqlite3
    
    db = PaperDatabase("paper_collection/data/papers.db")
    cursor = db.conn.cursor()
    
    # Count papers
    total = cursor.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    with_fulltext = cursor.execute(
        "SELECT COUNT(*) FROM papers WHERE is_full_text_pmc = 1"
    ).fetchone()[0]
    
    # Count by source
    cursor.execute("SELECT source, COUNT(*) FROM papers GROUP BY source")
    by_source = cursor.fetchall()
    
    # Count preprints
    preprints = cursor.execute(
        "SELECT COUNT(*) FROM papers WHERE journal LIKE '%preprint%'"
    ).fetchone()[0]
    
    print(f"\nCollection Statistics:")
    print(f"  Total papers: {total:,}")
    print(f"  With full text: {with_fulltext:,}")
    print(f"  Preprints: {preprints:,}")
    print(f"\nBy source:")
    for source, count in by_source:
        print(f"  - {source}: {count:,} papers")
    
    print(f"\nDatabase: paper_collection/data/papers.db")
    print(f"JSON export: paper_collection/data/papers_export.json")
    print("="*80 + "\n")
    
    db.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCollection interrupted by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
