#!/usr/bin/env python3
"""
Dry run for broad_aging collection - shows what will happen without actually collecting
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Bio import Entrez
from src.config import ENTREZ_EMAIL, ENTREZ_API_KEY, NUM_THREADS, BATCH_SIZE, CHECKPOINT_EVERY
from src.database import PaperDatabase

# Query
query = """(
  ("aging"[tiab] OR "ageing"[tiab] OR "senescence"[tiab] OR "longevity"[tiab]) AND
  (theory[tiab] OR theories[tiab] OR hypothes*[tiab] OR framework*[tiab] OR paradigm*[tiab] OR "ultimate cause"[tiab] OR "proximate cause"[tiab] OR "evolution*"[tiab])
  NOT (cosmetic*[tiab] OR sunscreen*[tiab] OR "facial"[tiab] OR dermatol*[tiab])
  NOT ("healthy aging"[tiab] OR wellbeing[tiab] OR "public health"[tiab])
  NOT ("religion"[tiab])
  NOT ("Cosmetics"[mh])
  NOT ("Skin"[mh] OR "Dermatology"[mh])
)"""

print("="*80)
print("DRY RUN: broad_aging Collection")
print("="*80)

# Step 1: Query count
print("\nStep 1: Verifying PubMed query...")
Entrez.email = ENTREZ_EMAIL
Entrez.api_key = ENTREZ_API_KEY

try:
    handle = Entrez.esearch(db="pubmed", term=query, retmax=0)
    record = Entrez.read(handle)
    handle.close()
    count = int(record["Count"])
    print(f"✓ Query will return: {count:,} papers")
except Exception as e:
    print(f"✗ Query failed: {e}")
    sys.exit(1)

# Step 2: Database check
print("\nStep 2: Checking database...")
db = PaperDatabase()
current_stats = db.get_statistics()
print(f"✓ Current papers in database: {current_stats['total_papers']:,}")

# Check if broad_aging exists
queries = db.get_all_queries()
broad_aging_exists = False
for q in queries:
    if q['description'] == 'broad_aging':
        broad_aging_exists = True
        papers_with_query = db.count_papers_by_query(q['id'])
        print(f"✓ Query 'broad_aging' already exists (ID: {q['id']})")
        print(f"  Papers already collected with this query: {papers_with_query:,}")
        break

if not broad_aging_exists:
    print(f"✓ Query 'broad_aging' will be created (new query ID will be assigned)")

# Step 3: Collection plan
print("\nStep 3: Collection plan...")
total_papers = count
already_in_db = current_stats['total_papers']  # Conservative estimate
papers_to_collect = max(0, total_papers - already_in_db)

batches = (total_papers + BATCH_SIZE - 1) // BATCH_SIZE
print(f"✓ Total batches: {batches:,} (batch size: {BATCH_SIZE})")
print(f"✓ Threads: {NUM_THREADS}")
print(f"✓ Checkpoints: Every {CHECKPOINT_EVERY} batches (~{CHECKPOINT_EVERY * BATCH_SIZE:,} papers)")

# Estimate time
# Conservative: 3 seconds per paper (metadata + full text + OpenAlex)
# With parallelization: divide by threads * batch_size
papers_per_minute = (NUM_THREADS * BATCH_SIZE) / 3 * 60
est_minutes = papers_to_collect / papers_per_minute
est_hours = est_minutes / 60

print(f"\n✓ Estimated papers to process: {papers_to_collect:,}")
print(f"  (Papers already in DB will be skipped: ~{already_in_db:,})")
print(f"✓ Estimated time: {est_hours:.1f} - {est_hours*2:.1f} hours")

# Step 4: What will be collected
print("\nStep 4: What will be collected for each paper...")
print("✓ PubMed metadata:")
print("  - PMID, PMCID, DOI")
print("  - Title, Abstract")
print("  - Authors, Journal, Year")
print("  - MeSH terms, Keywords")
print("✓ Full text (if available from PMC):")
print("  - Structured sections")
print("  - Cleaned text")
print("✓ OpenAlex enrichment (if DOI available):")
print("  - Citation count")
print("  - FWCI (Field-Weighted Citation Impact)")
print("  - Primary topic")
print("  - Open Access URL")
print("✓ Query tracking:")
print("  - query_id = 'broad_aging'")

# Step 5: Output files
print("\nStep 5: Output files that will be created/updated...")
print("✓ Database: paper_collection/data/papers.db")
print("  - All papers with metadata")
print("  - Query tracking table")
print("  - Collection statistics")
print("✓ JSON export: paper_collection/data/papers_export.json")
print("  - Complete export of all papers")
print("✓ Failed papers: paper_collection/data/failed_dois.json")
print("  - Papers without PMC full text")

# Step 6: Safety features
print("\nStep 6: Safety features...")
print("✓ Automatic deduplication (PMID primary key)")
print("✓ Resume capability (skips existing papers)")
print("✓ Progress checkpoints every 10 batches")
print("✓ Error recovery with retries")
print("✓ Rate limit handling with credential rotation")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"When you run scripts/run_full.py:")
print(f"  1. Query 'broad_aging' will be {'updated' if broad_aging_exists else 'created'}")
print(f"  2. System will search PubMed for {count:,} papers")
print(f"  3. Papers will be processed in {batches:,} batches")
print(f"  4. Each paper will be tagged with query_id = 'broad_aging'")
print(f"  5. Estimated completion: {est_hours:.1f} - {est_hours*2:.1f} hours")
print(f"  6. All data saved to: paper_collection/data/")
print("\nReady to proceed? Run:")
print("  python3 scripts/run_full.py")
print("="*80)

db.close()
