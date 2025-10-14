#!/usr/bin/env python3
"""
Migration script to add query tracking to the database.

This script:
1. Creates a 'queries' table to store search queries
2. Adds a 'query_id' column to the 'papers' table
3. Inserts the initial query used for the existing papers
4. Updates all existing papers to reference this query
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import DATABASE_PATH


def run_migration(db_path: str = DATABASE_PATH):
    """Run the migration to add query tracking"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Starting migration to add query tracking...")
    print(f"Database: {db_path}")
    
    # Check if migration is needed
    cursor.execute("PRAGMA table_info(papers)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'query_id' in columns:
        print("⚠️  Migration already applied - 'query_id' column already exists")
        response = input("Do you want to continue anyway? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled")
            return
    
    # Step 1: Create queries table
    print("\n1. Creating 'queries' table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_text TEXT NOT NULL,
            description TEXT,
            created_date TEXT NOT NULL
        )
    """)
    conn.commit()
    print("✓ Queries table created")
    
    # Step 2: Add query_id column to papers table (if not exists)
    if 'query_id' not in columns:
        print("\n2. Adding 'query_id' column to papers table...")
        cursor.execute("""
            ALTER TABLE papers ADD COLUMN query_id INTEGER
        """)
        conn.commit()
        print("✓ Column added")
    else:
        print("\n2. 'query_id' column already exists, skipping...")
    
    # Step 3: Insert the initial query
    print("\n3. Inserting initial query...")
    
    initial_query = """(
aging[Title] OR ageing[Title])
 AND ( theory[Title] OR theories[Title] OR hypothesis[Title] OR hypotheses[Title] OR paradigm[Title] OR paradigms[Title])
)
NOT
(Case Reports[Publication Type] OR "case report"[Title] OR "case reports"[Title] OR Clinical Trial[Publication Type] OR "protocol"[Title] OR "conference"[Title] OR "meeting"[Title] OR "well-being"[TI] OR "successful aging"[TI] OR "successful ageing"[TI] OR "ovarian"[TI] OR "liver"[TI] OR "kidne*"[TI] OR "skin"[TI] OR "religion"[TI] OR "enjoyment"[TI] OR "disease hypothesis"[TI] OR "healthy aging"[TI] OR "healthy ageing"[TI] OR "menopause"[TI] 
)"""
    
    description = "Initial query: Aging/ageing theories, hypotheses, and paradigms (excluding clinical trials, case reports, and specific exclusions)"
    created_date = datetime.now().isoformat()
    
    # Check if query already exists
    cursor.execute("SELECT id FROM queries WHERE query_text = ?", (initial_query,))
    existing = cursor.fetchone()
    
    if existing:
        query_id = existing[0]
        print(f"✓ Query already exists with ID: {query_id}")
    else:
        cursor.execute("""
            INSERT INTO queries (query_text, description, created_date)
            VALUES (?, ?, ?)
        """, (initial_query, description, created_date))
        query_id = cursor.lastrowid
        conn.commit()
        print(f"✓ Query inserted with ID: {query_id}")
    
    # Step 4: Update all existing papers to reference this query
    print("\n4. Updating existing papers with query_id...")
    
    cursor.execute("SELECT COUNT(*) FROM papers")
    total_papers = cursor.fetchone()[0]
    print(f"Found {total_papers} papers to update")
    
    cursor.execute("SELECT COUNT(*) FROM papers WHERE query_id IS NULL")
    papers_to_update = cursor.fetchone()[0]
    print(f"{papers_to_update} papers need query_id assignment")
    
    if papers_to_update > 0:
        cursor.execute("""
            UPDATE papers 
            SET query_id = ? 
            WHERE query_id IS NULL
        """, (query_id,))
        conn.commit()
        print(f"✓ Updated {papers_to_update} papers with query_id = {query_id}")
    else:
        print("✓ No papers need updating")
    
    # Verify the migration
    print("\n5. Verifying migration...")
    cursor.execute("SELECT COUNT(*) FROM queries")
    query_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM papers WHERE query_id IS NOT NULL")
    papers_with_query = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM papers WHERE query_id IS NULL")
    papers_without_query = cursor.fetchone()[0]
    
    print(f"✓ Total queries in database: {query_count}")
    print(f"✓ Papers with query_id: {papers_with_query}")
    print(f"✓ Papers without query_id: {papers_without_query}")
    
    # Show query details
    print("\n6. Query details:")
    cursor.execute("SELECT id, description, created_date FROM queries WHERE id = ?", (query_id,))
    row = cursor.fetchone()
    print(f"   Query ID: {row[0]}")
    print(f"   Description: {row[1]}")
    print(f"   Created: {row[2]}")
    
    conn.close()
    
    print("\n" + "="*70)
    print("✅ Migration completed successfully!")
    print("="*70)
    print("\nNext steps:")
    print("1. Update src/database.py to include query_id in table creation")
    print("2. Update src/models.py to include query_id in PaperMetadata")
    print("3. Update insert_paper() method to handle query_id")


def show_queries(db_path: str = DATABASE_PATH):
    """Display all queries in the database"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, query_text, description, created_date FROM queries ORDER BY id")
    queries = cursor.fetchall()
    
    if not queries:
        print("No queries found in database")
        return
    
    print("\nQueries in database:")
    print("="*70)
    for query_id, query_text, description, created_date in queries:
        print(f"\nQuery ID: {query_id}")
        print(f"Description: {description}")
        print(f"Created: {created_date}")
        print(f"Query text: {query_text[:100]}...")
        
        # Count papers using this query
        cursor.execute("SELECT COUNT(*) FROM papers WHERE query_id = ?", (query_id,))
        paper_count = cursor.fetchone()[0]
        print(f"Papers: {paper_count}")
        print("-"*70)
    
    conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Add query tracking to papers database")
    parser.add_argument("--show", action="store_true", help="Show all queries in database")
    parser.add_argument("--db", type=str, default=DATABASE_PATH, help="Database path")
    
    args = parser.parse_args()
    
    if args.show:
        show_queries(args.db)
    else:
        run_migration(args.db)
