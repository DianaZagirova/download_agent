#!/usr/bin/env python3
"""
Collect aging theory papers where terms appear in TITLE or ABSTRACT only
Uses field-specific search in Europe PMC
"""

from scripts.download_europepmc import collect_europepmc_papers

# Fixed query - all terms with TITLE or ABSTRACT field specifiers
query = """
(
  (TITLE:"theory of aging" OR ABSTRACT:"theory of aging") OR
  (TITLE:"aging theory" OR ABSTRACT:"aging theory") OR
  (TITLE:"ageing theory" OR ABSTRACT:"ageing theory") OR
  (TITLE:"theories of aging" OR ABSTRACT:"theories of aging") OR
  (TITLE:"theory of ageing" OR ABSTRACT:"theory of ageing") OR
  (TITLE:"theories of ageing" OR ABSTRACT:"theories of ageing") OR
  (TITLE:"antagonistic pleiotropy" OR ABSTRACT:"antagonistic pleiotropy") OR
  (TITLE:"programmed aging" OR ABSTRACT:"programmed aging") OR
  (TITLE:"damage accumulation theory" OR ABSTRACT:"damage accumulation theory") OR
  (TITLE:"disposable soma theory" OR ABSTRACT:"disposable soma theory") OR
  (TITLE:"mutation accumulation theory" OR ABSTRACT:"mutation accumulation theory") OR
  (TITLE:"free radical theory" OR ABSTRACT:"free radical theory") OR
  (TITLE:"oxidative stress theory" OR ABSTRACT:"oxidative stress theory") OR
  (TITLE:"hyperfunction theory" OR ABSTRACT:"hyperfunction theory") OR
  (TITLE:"hallmarks of aging" OR ABSTRACT:"hallmarks of aging") OR
  (TITLE:"pillars of aging" OR ABSTRACT:"pillars of aging")
)
"""

print("="*80)
print("AGING THEORIES - TITLE OR ABSTRACT SEARCH")
print("="*80)
print(f"\nQuery: {query[:200]}...")
print(f"\nField restriction: TITLE or ABSTRACT only")
print(f"Expected results: 5,000-10,000 papers")
print("="*80 + "\n")

# Run collection
collect_europepmc_papers(
    query=query.strip(),
    max_results=10000,
    include_preprints=True,
    use_threading=True,
    output_dir="aging_theories_title_abstract",
    query_description="Aging theories (title or abstract only)"
)

print("\n" + "="*80)
print("COLLECTION COMPLETE!")
print("="*80)

# Show statistics
from src.database import PaperDatabase

db = PaperDatabase("aging_theories_title_abstract/data/papers.db")
cursor = db.conn.cursor()

total = cursor.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
with_fulltext = cursor.execute(
    "SELECT COUNT(*) FROM papers WHERE is_full_text_pmc = 1"
).fetchone()[0]

print(f"\nResults:")
print(f"  Total papers: {total:,}")
print(f"  With full text: {with_fulltext:,}")
print(f"\nDatabase: aging_theories_title_abstract/data/papers.db")
print("="*80 + "\n")

db.close()
