#!/usr/bin/env python3
"""
Migration script to update existing database records with the new topic fields
"""
import sys
import os
import json
import sqlite3
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import DATABASE_PATH


def migrate_topic_fields(db_path=None):
    """
    Migrate existing database records to populate the new topic fields
    from the primary_topic JSON column.
    
    Args:
        db_path: Path to the database file (uses default if None)
    """
    if db_path is None:
        db_path = DATABASE_PATH
    
    print(f"Opening database: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check if the new columns exist
    try:
        cursor.execute("SELECT topic_name, topic_subfield, topic_field, topic_domain FROM papers LIMIT 1")
    except sqlite3.OperationalError:
        print("Error: New topic columns don't exist in the database schema.")
        print("Please update your database schema first.")
        conn.close()
        return
    
    # Get all papers with primary_topic data
    cursor.execute("SELECT pmid, primary_topic FROM papers WHERE primary_topic IS NOT NULL")
    papers = cursor.fetchall()
    
    if not papers:
        print("No papers with primary_topic data found.")
        conn.close()
        return
    
    print(f"Found {len(papers)} papers with primary_topic data to migrate.")
    
    # Confirm with user
    confirm = input("Proceed with migration? (y/n): ")
    if confirm.lower() != 'y':
        print("Migration cancelled.")
        conn.close()
        return
    
    # Update each paper
    updated = 0
    for paper in tqdm(papers, desc="Migrating papers"):
        try:
            pmid = paper['pmid']
            primary_topic = json.loads(paper['primary_topic'])
            
            # Extract topic fields
            topic_name = primary_topic.get('display_name')
            topic_subfield = primary_topic.get('subfield', {}).get('display_name') if 'subfield' in primary_topic else None
            topic_field = primary_topic.get('field', {}).get('display_name') if 'field' in primary_topic else None
            topic_domain = primary_topic.get('domain', {}).get('display_name') if 'domain' in primary_topic else None
            
            # Update the record
            cursor.execute("""
                UPDATE papers 
                SET topic_name = ?,
                    topic_subfield = ?,
                    topic_field = ?,
                    topic_domain = ?
                WHERE pmid = ?
            """, (topic_name, topic_subfield, topic_field, topic_domain, pmid))
            
            updated += 1
        except Exception as e:
            print(f"Error updating paper {paper['pmid']}: {str(e)}")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"\nMigration completed successfully!")
    print(f"Updated {updated} out of {len(papers)} papers.")
    
    # Verify the migration
    verify_migration(db_path)


def verify_migration(db_path):
    """
    Verify that the migration was successful by checking a few records.
    
    Args:
        db_path: Path to the database file
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get a few papers with topic data
    cursor.execute("""
        SELECT pmid, primary_topic, topic_name, topic_subfield, topic_field, topic_domain
        FROM papers 
        WHERE topic_name IS NOT NULL
        LIMIT 5
    """)
    papers = cursor.fetchall()
    
    print("\nVerification Sample:")
    for paper in papers:
        print(f"\nPMID: {paper['pmid']}")
        print(f"Topic Name: {paper['topic_name']}")
        print(f"Topic Subfield: {paper['topic_subfield']}")
        print(f"Topic Field: {paper['topic_field']}")
        print(f"Topic Domain: {paper['topic_domain']}")
    
    conn.close()


if __name__ == "__main__":
    print("="*60)
    print("TOPIC FIELDS MIGRATION SCRIPT")
    print("="*60)
    print("\nThis script will update existing database records to populate")
    print("the new topic fields from the primary_topic JSON column.")
    print("\nMake sure to back up your database before running this script!")
    
    migrate_topic_fields()
