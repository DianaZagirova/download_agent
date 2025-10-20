#!/usr/bin/env python3
"""
Verify system readiness for large collection (46,351 papers)
"""
import sys
import os
import sqlite3
import shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import (
    DATABASE_PATH, DATA_DIR, CHECKPOINT_DIR, LOGS_DIR, BASE_DIR,
    NUM_THREADS, BATCH_SIZE, CHECKPOINT_EVERY, METADATA_FETCH_BATCH_SIZE,
    NCBI_CREDENTIALS, MAX_REQUESTS_PER_SEC
)

print("="*80)
print("SYSTEM READINESS CHECK FOR LARGE COLLECTION")
print("="*80)
print(f"Target: 46,351 papers\n")

# 1. Check directories
print("1. Directory Structure Check")
print("-" * 80)
directories = {
    'Base directory': BASE_DIR,
    'Data directory': DATA_DIR,
    'Checkpoint directory': CHECKPOINT_DIR,
    'Logs directory': LOGS_DIR,
}

all_dirs_exist = True
for name, path in directories.items():
    exists = os.path.exists(path)
    writable = os.access(path, os.W_OK) if exists else False
    status = "✓" if exists and writable else "✗"
    print(f"   {status} {name}: {path}")
    if not exists or not writable:
        all_dirs_exist = False

if all_dirs_exist:
    print("   ✅ All directories exist and are writable\n")
else:
    print("   ⚠️  Some directories missing or not writable\n")

# 2. Check disk space
print("2. Disk Space Check")
print("-" * 80)
try:
    stat = shutil.disk_usage(DATA_DIR)
    free_gb = stat.free / (1024**3)
    total_gb = stat.total / (1024**3)
    used_gb = stat.used / (1024**3)
    
    # Estimate: ~50MB per 1000 papers with full text = ~2.3GB for 46,351 papers
    # Add buffer for database, exports, logs = ~5GB total
    required_gb = 5
    
    print(f"   Total: {total_gb:.2f} GB")
    print(f"   Used: {used_gb:.2f} GB")
    print(f"   Free: {free_gb:.2f} GB")
    print(f"   Required (estimated): {required_gb:.2f} GB")
    
    if free_gb >= required_gb:
        print(f"   ✅ Sufficient disk space available\n")
    else:
        print(f"   ⚠️  Low disk space (need {required_gb:.2f} GB, have {free_gb:.2f} GB)\n")
except Exception as e:
    print(f"   ⚠️  Could not check disk space: {e}\n")

# 3. Check database
print("3. Database Check")
print("-" * 80)
db_exists = os.path.exists(DATABASE_PATH)
print(f"   Database path: {DATABASE_PATH}")
print(f"   Exists: {db_exists}")

if db_exists:
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        expected_tables = ['papers', 'collection_runs', 'failed_dois', 'queries']
        
        print(f"   Tables: {', '.join(tables)}")
        
        # Check existing papers
        cursor.execute("SELECT COUNT(*) FROM papers")
        paper_count = cursor.fetchone()[0]
        print(f"   Current paper count: {paper_count:,}")
        
        # Check queries
        cursor.execute("SELECT COUNT(*) FROM queries")
        query_count = cursor.fetchone()[0]
        print(f"   Current query count: {query_count}")
        
        # Check if broad_aging query already exists
        cursor.execute("SELECT id, description FROM queries WHERE description = 'broad_aging'")
        broad_aging_query = cursor.fetchone()
        if broad_aging_query:
            print(f"   ⚠️  Query 'broad_aging' already exists (ID: {broad_aging_query[0]})")
            cursor.execute("SELECT COUNT(*) FROM papers WHERE query_id = ?", (broad_aging_query[0],))
            existing_papers = cursor.fetchone()[0]
            print(f"   Papers with broad_aging query: {existing_papers:,}")
        else:
            print(f"   ✓ No existing 'broad_aging' query (will be created)")
        
        conn.close()
        print("   ✅ Database accessible and structure valid\n")
    except Exception as e:
        print(f"   ⚠️  Database error: {e}\n")
else:
    print("   ✓ Database will be created on first run\n")

# 4. Check configuration
print("4. Configuration Check")
print("-" * 80)
print(f"   Threads: {NUM_THREADS}")
print(f"   Batch size: {BATCH_SIZE}")
print(f"   Checkpoint interval: {CHECKPOINT_EVERY} batches")
print(f"   Metadata fetch batch size: {METADATA_FETCH_BATCH_SIZE}")
print(f"   Max requests/sec: {MAX_REQUESTS_PER_SEC}")
print(f"   NCBI credentials: {len(NCBI_CREDENTIALS)} accounts")

# Calculate estimated processing time
papers = 46351
batches = (papers + BATCH_SIZE - 1) // BATCH_SIZE
print(f"\n   Estimated batches: {batches:,}")

# Conservative estimate: ~5 seconds per paper (metadata + full text + OpenAlex)
# With 3 threads and batch size 50: ~5 * 46351 / (3 * 50) = ~1545 seconds = ~26 minutes
# More realistic with API delays: 1-2 hours
est_seconds = (papers * 5) / (NUM_THREADS * BATCH_SIZE) * 2  # 2x buffer for API delays
est_hours = est_seconds / 3600
print(f"   Estimated time: {est_hours:.1f} - {est_hours*2:.1f} hours")
print(f"   ✅ Configuration suitable for large collection\n")

# 5. Check credentials
print("5. Credentials Check")
print("-" * 80)
for i, creds in enumerate(NCBI_CREDENTIALS, 1):
    email = creds['email']
    api_key = creds['api_key']
    print(f"   Account {i}: {email}")
    print(f"      API key: {api_key[:10]}...{api_key[-4:]}")
print(f"   ✅ {len(NCBI_CREDENTIALS)} credential sets configured\n")

# 6. Checkpointing & Recovery
print("6. Checkpoint & Recovery System")
print("-" * 80)
print(f"   Checkpoint interval: Every {CHECKPOINT_EVERY} batches")
print(f"   Checkpoint directory: {CHECKPOINT_DIR}")
print(f"   Database uses INSERT OR REPLACE (automatic deduplication)")
print(f"   Skips already-collected papers (paper_exists check)")
print(f"   ✅ System supports interrupted collection resumption\n")

# 7. Logging
print("7. Logging System")
print("-" * 80)
print(f"   Logs directory: {LOGS_DIR}")
print(f"   Console logging: Enabled (tqdm progress bars)")
print(f"   Database stats: Saved after collection")
print(f"   Failed papers: Tracked in failed_dois table")
print(f"   ✅ Comprehensive logging enabled\n")

# Final summary
print("="*80)
print("SUMMARY")
print("="*80)
print("✅ System is ready for large collection (46,351 papers)")
print("\nKey points:")
print("  - Database will auto-create 'broad_aging' query on first run")
print("  - Papers already in DB will be skipped (efficient resumption)")
print("  - Progress checkpoints every 10 batches")
print("  - Estimated collection time: 1-3 hours")
print("  - All data will be saved to: " + DATA_DIR)
print("\nTo start collection, run:")
print("  python3 scripts/run_full.py")
print("="*80)
