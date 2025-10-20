#!/usr/bin/env python3
"""
Merge aging_theories_collection database into paper_collection database
Intelligently merges fields: prefers filled over empty, longest full_text, etc.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import PaperDatabase
from src.models import PaperMetadata
import sqlite3
from typing import Optional
import json

def merge_field(existing_value, new_value, prefer_longest=False):
    """
    Merge two field values intelligently.
    
    Args:
        existing_value: Value from target database
        new_value: Value from source database
        prefer_longest: If True, prefer the longest value (for text fields)
    
    Returns:
        Merged value
    """
    # If both are None/empty, return None
    if not existing_value and not new_value:
        return None
    
    # If only one exists, use it
    if not existing_value:
        return new_value
    if not new_value:
        return existing_value
    
    # Both exist - apply merge logic
    if prefer_longest:
        # For text fields, prefer the longest
        if len(str(new_value)) > len(str(existing_value)):
            return new_value
        return existing_value
    else:
        # Prefer existing value if both exist
        return existing_value


def merge_list_field(existing_list, new_list):
    """
    Merge two list fields by combining and deduplicating.
    
    Args:
        existing_list: List from target database
        new_list: List from source database
    
    Returns:
        Merged list
    """
    if not existing_list and not new_list:
        return []
    if not existing_list:
        return new_list
    if not new_list:
        return existing_list
    
    # Combine and deduplicate
    combined = existing_list + [item for item in new_list if item not in existing_list]
    return combined


def merge_papers(existing: PaperMetadata, new: PaperMetadata) -> PaperMetadata:
    """
    Intelligently merge two paper metadata objects.
    
    Merge rules:
    - Prefer filled fields over empty
    - For full_text: use the longest version
    - For abstract: use the longest version
    - For lists (authors, keywords, mesh_terms): combine and deduplicate
    - For numeric fields: prefer non-zero/non-None
    
    Args:
        existing: Existing paper in target database
        new: New paper from source database
    
    Returns:
        Merged PaperMetadata
    """
    
    # Start with existing paper
    merged = PaperMetadata(
        pmid=existing.pmid or new.pmid,
        pmcid=merge_field(existing.pmcid, new.pmcid),
        doi=merge_field(existing.doi, new.doi),
        title=merge_field(existing.title, new.title, prefer_longest=True),
        abstract=merge_field(existing.abstract, new.abstract, prefer_longest=True),
        full_text=merge_field(existing.full_text, new.full_text, prefer_longest=True),
        full_text_sections=existing.full_text_sections if existing.full_text_sections else new.full_text_sections,
        mesh_terms=merge_list_field(existing.mesh_terms, new.mesh_terms),
        keywords=merge_list_field(existing.keywords, new.keywords),
        authors=merge_list_field(existing.authors, new.authors),
        year=merge_field(existing.year, new.year),
        date_published=merge_field(existing.date_published, new.date_published),
        journal=merge_field(existing.journal, new.journal),
        is_full_text_pmc=existing.is_full_text_pmc or new.is_full_text_pmc,  # True if either has it
        oa_url=merge_field(existing.oa_url, new.oa_url),
        primary_topic=existing.primary_topic if existing.primary_topic else new.primary_topic,
        citation_normalized_percentile=merge_field(existing.citation_normalized_percentile, new.citation_normalized_percentile),
        cited_by_count=merge_field(existing.cited_by_count, new.cited_by_count),
        fwci=merge_field(existing.fwci, new.fwci),
        collection_date=existing.collection_date,  # Keep original collection date
        openalex_retrieved=existing.openalex_retrieved or new.openalex_retrieved,
        query_id=existing.query_id,  # Keep original query_id
        source=merge_field(existing.source, new.source)
    )
    
    return merged


def merge_databases(
    source_db_path: str,
    target_db_path: str,
    dry_run: bool = False
):
    """
    Merge source database into target database.
    
    Args:
        source_db_path: Path to source database (aging_theories_collection)
        target_db_path: Path to target database (paper_collection)
        dry_run: If True, only report what would be done without making changes
    """
    
    print("="*80)
    print("DATABASE MERGE UTILITY")
    print("="*80)
    print(f"Source: {source_db_path}")
    print(f"Target: {target_db_path}")
    print(f"Mode: {'DRY RUN (no changes will be made)' if dry_run else 'LIVE (will modify target database)'}")
    print("="*80 + "\n")
    
    # Open both databases
    source_db = PaperDatabase(source_db_path)
    target_db = PaperDatabase(target_db_path)
    
    # Get statistics before merge
    print("📊 Initial Statistics:")
    print(f"  Source DB: {len(source_db.get_all_papers()):,} papers")
    print(f"  Target DB: {len(target_db.get_all_papers()):,} papers")
    print()
    
    # Get all papers from source
    source_papers = source_db.get_all_papers()
    
    # Counters
    added_count = 0
    merged_count = 0
    skipped_count = 0
    errors = []
    
    print(f"Processing {len(source_papers):,} papers from source database...")
    print()
    
    for i, source_paper in enumerate(source_papers):
        if (i + 1) % 100 == 0:
            print(f"  Progress: {i+1:,}/{len(source_papers):,} papers processed...", end='\r')
        
        try:
            # Check if paper exists by DOI (primary) or PMID (fallback)
            existing_paper = None
            
            if source_paper.doi:
                existing_paper = target_db.get_paper_by_doi(source_paper.doi)
            
            if not existing_paper and source_paper.pmid:
                existing_paper = target_db.get_paper(source_paper.pmid)
            
            if existing_paper:
                # Paper exists - merge it
                merged_paper = merge_papers(existing_paper, source_paper)
                
                if not dry_run:
                    target_db.insert_paper(merged_paper)
                
                merged_count += 1
                
                # Show example of what was merged (first 5 only)
                if merged_count <= 5:
                    print(f"\n✅ MERGED: DOI={source_paper.doi or 'N/A'}")
                    print(f"   Title: {source_paper.title[:80]}...")
                    
                    # Show what changed
                    changes = []
                    if not existing_paper.full_text and merged_paper.full_text:
                        changes.append("Added full_text")
                    elif existing_paper.full_text and merged_paper.full_text and len(merged_paper.full_text) > len(existing_paper.full_text):
                        changes.append(f"Updated full_text (longer: {len(merged_paper.full_text)} vs {len(existing_paper.full_text)} chars)")
                    
                    if not existing_paper.abstract and merged_paper.abstract:
                        changes.append("Added abstract")
                    elif existing_paper.abstract and merged_paper.abstract and len(merged_paper.abstract) > len(existing_paper.abstract):
                        changes.append(f"Updated abstract (longer: {len(merged_paper.abstract)} vs {len(existing_paper.abstract)} chars)")
                    
                    if len(merged_paper.authors) > len(existing_paper.authors):
                        changes.append(f"Merged authors ({len(existing_paper.authors)} → {len(merged_paper.authors)})")
                    
                    if len(merged_paper.keywords) > len(existing_paper.keywords):
                        changes.append(f"Merged keywords ({len(existing_paper.keywords)} → {len(merged_paper.keywords)})")
                    
                    if changes:
                        print(f"   Changes: {', '.join(changes)}")
                    else:
                        print(f"   Changes: No significant changes")
            
            else:
                # Paper doesn't exist - add it
                if not dry_run:
                    target_db.insert_paper(source_paper)
                
                added_count += 1
                
                # Show example of what was added (first 5 only)
                if added_count <= 5:
                    print(f"\n➕ ADDED: DOI={source_paper.doi or 'N/A'}")
                    print(f"   Title: {source_paper.title[:80]}...")
        
        except Exception as e:
            errors.append((source_paper.pmid or source_paper.doi, str(e)))
            skipped_count += 1
    
    print(f"\n  Progress: {len(source_papers):,}/{len(source_papers):,} papers processed... DONE\n")
    
    # Final statistics
    print("="*80)
    print("MERGE COMPLETE!")
    print("="*80)
    print(f"\n📊 Results:")
    print(f"  ✅ Papers added: {added_count:,}")
    print(f"  🔄 Papers merged: {merged_count:,}")
    print(f"  ❌ Errors/Skipped: {skipped_count:,}")
    print(f"  📝 Total processed: {len(source_papers):,}")
    
    if not dry_run:
        print(f"\n  Final target DB size: {len(target_db.get_all_papers()):,} papers")
    
    if errors:
        print(f"\n⚠️  Errors encountered:")
        for pmid_or_doi, error in errors[:10]:  # Show first 10 errors
            print(f"  - {pmid_or_doi}: {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
    
    print("\n" + "="*80)
    
    # Close databases
    source_db.close()
    target_db.close()
    
    return {
        'added': added_count,
        'merged': merged_count,
        'skipped': skipped_count,
        'errors': errors
    }


def main():
    """Main execution"""
    
    # Database paths
    source_db = "/home/diana.z/hack/download_papers_pubmed/aging_theories_collection/data/papers.db"
    target_db = "/home/diana.z/hack/download_papers_pubmed/paper_collection/data/papers.db"
    
    # Check if databases exist
    if not os.path.exists(source_db):
        print(f"❌ Source database not found: {source_db}")
        return
    
    if not os.path.exists(target_db):
        print(f"❌ Target database not found: {target_db}")
        return
    
    # Run merge
    print("\n⚠️  This will merge aging_theories_collection into paper_collection")
    print("   Press Ctrl+C to cancel, or Enter to continue...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nMerge cancelled by user.")
        return
    
    # First do a dry run to show what will happen
    print("\n" + "="*80)
    print("STEP 1: DRY RUN (Preview)")
    print("="*80 + "\n")
    
    dry_run_results = merge_databases(source_db, target_db, dry_run=True)
    
    print("\n\n⚠️  Dry run complete. Proceed with actual merge?")
    print("   Press Ctrl+C to cancel, or Enter to continue...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nMerge cancelled by user.")
        return
    
    # Now do the actual merge
    print("\n" + "="*80)
    print("STEP 2: LIVE MERGE")
    print("="*80 + "\n")
    
    results = merge_databases(source_db, target_db, dry_run=False)
    
    print("\n✅ Merge complete! You can now safely delete aging_theories_collection if desired.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMerge interrupted by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
