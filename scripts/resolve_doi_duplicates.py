#!/usr/bin/env python3
"""
Resolve DOI duplicates in the papers database using various strategies
"""
import sys
import os
import sqlite3
import json
from datetime import datetime
from typing import List, Dict
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_duplicate_dois(cursor) -> List[tuple]:
    """Get list of duplicate DOIs"""
    cursor.execute("""
        SELECT doi, COUNT(*) as count
        FROM papers
        WHERE doi IS NOT NULL AND doi != ''
        GROUP BY doi
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    """)
    return cursor.fetchall()


def get_papers_by_doi(cursor, doi: str) -> List[Dict]:
    """Get all papers with a specific DOI"""
    cursor.execute("""
        SELECT * FROM papers WHERE doi = ?
        ORDER BY collection_date DESC, pmid
    """, (doi,))
    return [dict(row) for row in cursor.fetchall()]


def strategy_keep_recent(conn, dry_run=True):
    """
    Strategy 1: Keep the most recently collected entry for each duplicate DOI
    """
    cursor = conn.cursor()
    duplicates = get_duplicate_dois(cursor)
    
    print("="*80)
    print("STRATEGY: Keep Most Recent Entry")
    print("="*80)
    print(f"Mode: {'DRY RUN (no changes will be made)' if dry_run else 'LIVE (changes will be applied)'}")
    print()
    
    if not duplicates:
        print("✅ No duplicates found!")
        return
    
    total_to_delete = 0
    deleted_pmids = []
    
    for dup in duplicates:
        doi = dup['doi']
        papers = get_papers_by_doi(cursor, doi)
        
        # Keep the first one (most recent by collection_date)
        keep_paper = papers[0]
        delete_papers = papers[1:]
        
        print(f"DOI: {doi}")
        print(f"  ✓ KEEP:   PMID {keep_paper['pmid']} (collected: {keep_paper['collection_date']})")
        
        for paper in delete_papers:
            print(f"  ✗ DELETE: PMID {paper['pmid']} (collected: {paper['collection_date']})")
            total_to_delete += 1
            deleted_pmids.append(paper['pmid'])
        print()
    
    print(f"Summary: Will delete {total_to_delete} duplicate entries")
    
    if not dry_run:
        print("\nDeleting duplicate entries...")
        for pmid in deleted_pmids:
            cursor.execute("DELETE FROM papers WHERE pmid = ?", (pmid,))
        conn.commit()
        print(f"✅ Deleted {total_to_delete} duplicate entries")
    else:
        print("\nTo apply these changes, run with --apply flag:")
        print("  python scripts/resolve_doi_duplicates.py --strategy keep-recent --apply")


def strategy_keep_fulltext(conn, dry_run=True):
    """
    Strategy 2: Keep entry with full text, fall back to most recent if ambiguous
    """
    cursor = conn.cursor()
    duplicates = get_duplicate_dois(cursor)
    
    print("="*80)
    print("STRATEGY: Keep Entry with Full Text")
    print("="*80)
    print(f"Mode: {'DRY RUN (no changes will be made)' if dry_run else 'LIVE (changes will be applied)'}")
    print()
    
    if not duplicates:
        print("✅ No duplicates found!")
        return
    
    total_to_delete = 0
    deleted_pmids = []
    
    for dup in duplicates:
        doi = dup['doi']
        papers = get_papers_by_doi(cursor, doi)
        
        # Separate papers with and without full text
        with_fulltext = [p for p in papers if p['is_full_text_pmc']]
        without_fulltext = [p for p in papers if not p['is_full_text_pmc']]
        
        # Decide which to keep
        if len(with_fulltext) == 1:
            # Clear winner: only one has full text
            keep_paper = with_fulltext[0]
            delete_papers = [p for p in papers if p['pmid'] != keep_paper['pmid']]
            reason = "has full text"
        elif len(with_fulltext) > 1:
            # Multiple with full text: keep most recent
            keep_paper = with_fulltext[0]  # Already sorted by date
            delete_papers = [p for p in papers if p['pmid'] != keep_paper['pmid']]
            reason = "has full text and most recent"
        else:
            # None have full text: keep most recent
            keep_paper = papers[0]
            delete_papers = papers[1:]
            reason = "most recent (none have full text)"
        
        print(f"DOI: {doi}")
        print(f"  ✓ KEEP:   PMID {keep_paper['pmid']} ({reason})")
        
        for paper in delete_papers:
            ft_status = "has full text" if paper['is_full_text_pmc'] else "no full text"
            print(f"  ✗ DELETE: PMID {paper['pmid']} ({ft_status})")
            total_to_delete += 1
            deleted_pmids.append(paper['pmid'])
        print()
    
    print(f"Summary: Will delete {total_to_delete} duplicate entries")
    
    if not dry_run:
        print("\nDeleting duplicate entries...")
        for pmid in deleted_pmids:
            cursor.execute("DELETE FROM papers WHERE pmid = ?", (pmid,))
        conn.commit()
        print(f"✅ Deleted {total_to_delete} duplicate entries")
    else:
        print("\nTo apply these changes, run with --apply flag:")
        print("  python scripts/resolve_doi_duplicates.py --strategy keep-fulltext --apply")


def strategy_merge(conn, dry_run=True):
    """
    Strategy 3: Merge duplicate entries, keeping most complete data
    """
    cursor = conn.cursor()
    duplicates = get_duplicate_dois(cursor)
    
    print("="*80)
    print("STRATEGY: Merge Duplicates")
    print("="*80)
    print(f"Mode: {'DRY RUN (no changes will be made)' if dry_run else 'LIVE (changes will be applied)'}")
    print()
    
    if not duplicates:
        print("✅ No duplicates found!")
        return
    
    for dup in duplicates:
        doi = dup['doi']
        papers = get_papers_by_doi(cursor, doi)
        
        print(f"DOI: {doi}")
        print(f"  Merging {len(papers)} entries:")
        
        # Choose the "primary" entry (most recent)
        primary = papers[0]
        others = papers[1:]
        
        merged_data = dict(primary)
        changes = []
        
        # Merge logic: keep non-null values from all entries
        for other in others:
            for key, value in other.items():
                if key == 'pmid':
                    continue  # Don't merge PMIDs
                
                # If primary is null/empty but other has value, use other's value
                if (not merged_data[key] or merged_data[key] == '') and value and value != '':
                    changes.append(f"    - Updated {key}: {merged_data[key]} → {value}")
                    merged_data[key] = value
        
        if changes:
            print(f"  Primary PMID: {primary['pmid']}")
            print(f"  Changes from merge:")
            for change in changes:
                print(change)
        else:
            print(f"  Primary PMID: {primary['pmid']} (no additional data to merge)")
        
        print(f"  Will delete: {', '.join([p['pmid'] for p in others])}")
        print()
        
        if not dry_run:
            # Update primary with merged data
            update_fields = ', '.join([f"{k} = ?" for k in merged_data.keys() if k != 'pmid'])
            update_values = [v for k, v in merged_data.items() if k != 'pmid']
            update_values.append(primary['pmid'])
            
            cursor.execute(f"""
                UPDATE papers
                SET {update_fields}
                WHERE pmid = ?
            """, update_values)
            
            # Delete others
            for other in others:
                cursor.execute("DELETE FROM papers WHERE pmid = ?", (other['pmid'],))
    
    if not dry_run:
        conn.commit()
        print(f"✅ Merged and deleted duplicates")
    else:
        print("\nTo apply these changes, run with --apply flag:")
        print("  python scripts/resolve_doi_duplicates.py --strategy merge --apply")


def strategy_export(conn, output_path=None):
    """
    Strategy 4: Export duplicates for manual review
    """
    cursor = conn.cursor()
    duplicates = get_duplicate_dois(cursor)
    
    print("="*80)
    print("STRATEGY: Export for Manual Review")
    print("="*80)
    
    if not duplicates:
        print("✅ No duplicates found!")
        return
    
    if output_path is None:
        output_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'paper_collection', 'data', 'doi_duplicates_export.json'
        )
    
    export_data = []
    
    for dup in duplicates:
        doi = dup['doi']
        papers = get_papers_by_doi(cursor, doi)
        
        export_data.append({
            'doi': doi,
            'count': len(papers),
            'papers': papers
        })
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'export_date': datetime.now().isoformat(),
            'total_duplicate_groups': len(duplicates),
            'total_duplicate_entries': sum(d['count'] for d in duplicates),
            'duplicates': export_data
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Exported {len(duplicates)} duplicate groups to:")
    print(f"   {output_path}")
    print(f"\nYou can review this file and manually decide which entries to keep.")


def backup_database(db_path: str) -> str:
    """Create a backup of the database"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = db_path.replace('.db', f'_backup_{timestamp}.db')
    
    import shutil
    shutil.copy2(db_path, backup_path)
    return backup_path


def main():
    parser = argparse.ArgumentParser(
        description='Resolve DOI duplicates in papers database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (preview changes without applying)
  python scripts/resolve_doi_duplicates.py --strategy keep-recent
  
  # Apply changes (with automatic backup)
  python scripts/resolve_doi_duplicates.py --strategy keep-recent --apply
  
  # Export for manual review
  python scripts/resolve_doi_duplicates.py --strategy export
  
Strategies:
  keep-recent   : Keep most recently collected entry (RECOMMENDED)
  keep-fulltext : Keep entry with full text from PMC
  merge         : Merge duplicate entries, keeping most complete data
  export        : Export duplicates to JSON for manual review
        """
    )
    
    parser.add_argument(
        '--strategy',
        required=True,
        choices=['keep-recent', 'keep-fulltext', 'merge', 'export'],
        help='Strategy to use for resolving duplicates'
    )
    
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply changes (default is dry run)'
    )
    
    parser.add_argument(
        '--db-path',
        help='Path to database (default: paper_collection/data/papers.db)'
    )
    
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip automatic backup (not recommended)'
    )
    
    args = parser.parse_args()
    
    # Get database path
    if args.db_path:
        db_path = args.db_path
    else:
        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'paper_collection', 'data', 'papers.db'
        )
    
    if not os.path.exists(db_path):
        print(f"❌ Error: Database not found at {db_path}")
        sys.exit(1)
    
    # Create backup if applying changes
    if args.apply and not args.no_backup and args.strategy != 'export':
        print("Creating backup...")
        backup_path = backup_database(db_path)
        print(f"✅ Backup created: {backup_path}\n")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # Execute strategy
        if args.strategy == 'keep-recent':
            strategy_keep_recent(conn, dry_run=not args.apply)
        elif args.strategy == 'keep-fulltext':
            strategy_keep_fulltext(conn, dry_run=not args.apply)
        elif args.strategy == 'merge':
            strategy_merge(conn, dry_run=not args.apply)
        elif args.strategy == 'export':
            strategy_export(conn)
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()
