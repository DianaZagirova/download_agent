#!/usr/bin/env python3
"""
Main orchestrator for Europe PMC paper collection system
Searches ALL Europe PMC content: published papers + preprints
"""
import sys
import time
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from typing import List, Tuple, Optional

from src.models import PaperMetadata, CollectionStats
from src.europepmc_extractor import (
    search_europepmc, extract_europepmc_metadata, get_paper_statistics
)
from src.openalex_extractor import enrich_with_openalex
from src.pubmed_extractor import try_all_fulltext_sources  # Reuse for PMC papers
from src.database import PaperDatabase
from src.config import NUM_THREADS, BATCH_SIZE, CHECKPOINT_EVERY


def process_batch(paper_batch: List[dict], db: PaperDatabase, query_id: int = None, skip_existing: bool = True) -> Tuple[int, int, int, int, int, int]:
    """
    Process a batch of papers from Europe PMC.
    
    Args:
        paper_batch: List of paper dictionaries from Europe PMC API
        db: Database handler
        query_id: Query ID to assign to papers
        skip_existing: If True, skip ALL existing papers (no enrichment)
        
    Returns:
        Tuple of (processed, with_fulltext, with_openalex, failed, skipped, enriched)
    """
    processed = 0
    with_fulltext = 0
    with_openalex = 0
    failed = 0
    skipped = 0
    enriched = 0
    
    # Separate papers into: new papers, papers needing enrichment, and papers to skip
    papers_to_process = []
    papers_to_enrich = []
    
    for paper in paper_batch:
        pmid = paper.get('pmid')
        doi = paper.get('doi')
        identifier = pmid or doi
        
        if not identifier:
            continue
        
        # Check if paper needs enrichment
        needs_enrichment, existing_paper = db.paper_needs_enrichment(identifier)
        
        if existing_paper is None:
            # Paper doesn't exist - add to new papers list
            papers_to_process.append(paper)
        elif needs_enrichment and not skip_existing:
            # Paper exists but needs enrichment (only if enrichment is enabled)
            metadata = extract_europepmc_metadata(paper)
            if metadata:
                # Merge with existing data (keep existing query_id, etc.)
                metadata.query_id = existing_paper.query_id
                papers_to_enrich.append(metadata)
        else:
            # Paper exists - skip (either complete OR skip_existing=True)
            skipped += 1
    
    if not papers_to_process and not papers_to_enrich:
        return processed, with_fulltext, with_openalex, failed, skipped, enriched
    
    # Extract metadata for all papers
    all_metadata = []
    for paper in papers_to_process:
        metadata = extract_europepmc_metadata(paper)
        if metadata:
            all_metadata.append(metadata)
        else:
            failed += 1
    
    # Try to get full text for papers with PMCIDs (using existing PubMed infrastructure)
    from concurrent.futures import ThreadPoolExecutor as FullTextExecutor
    
    def fetch_fulltext_for_paper(metadata):
        """Helper to fetch full text for a single paper"""
        # Only try for papers with PMCIDs (published papers)
        if metadata.pmcid:
            full_text, sections = try_all_fulltext_sources(metadata)
            if full_text:
                metadata.full_text = full_text
                metadata.full_text_sections = sections
                metadata.is_full_text_pmc = True
        return metadata
    
    # Parallel full text fetching for papers with PMCIDs
    papers_with_pmcid = [m for m in all_metadata if m.pmcid]
    
    if papers_with_pmcid:
        with FullTextExecutor(max_workers=min(2, len(papers_with_pmcid))) as ft_executor:
            futures = {ft_executor.submit(fetch_fulltext_for_paper, paper): paper 
                      for paper in papers_with_pmcid}
            for future in futures:
                try:
                    future.result()  # Updates metadata in place
                except Exception as e:
                    print(f"Error fetching full text: {e}")
    
    # Assign query_id
    if query_id is not None:
        for metadata in all_metadata:
            if metadata:
                metadata.query_id = query_id
    
    # Parallelize OpenAlex enrichment
    papers_with_doi = [m for m in all_metadata if m and m.doi]
    
    if papers_with_doi:
        with FullTextExecutor(max_workers=min(3, len(papers_with_doi))) as oa_executor:
            futures = {oa_executor.submit(enrich_with_openalex, paper): paper 
                      for paper in papers_with_doi}
            enriched_papers = []
            for future in futures:
                try:
                    enriched_papers.append(future.result())
                except Exception as e:
                    print(f"Error enriching with OpenAlex: {e}")
                    enriched_papers.append(futures[future])
    else:
        enriched_papers = []
    
    # Add papers without DOIs
    papers_without_doi = [m for m in all_metadata if m and not m.doi]
    all_papers_final = enriched_papers + papers_without_doi
    
    # Enrich existing papers that are missing abstract or full text
    if papers_to_enrich:
        print(f"  📝 Enriching {len(papers_to_enrich)} existing papers...")
        with FullTextExecutor(max_workers=2) as ft_executor:
            futures = {ft_executor.submit(fetch_fulltext_for_paper, paper): paper 
                      for paper in papers_to_enrich}
            for future in futures:
                try:
                    enriched_paper = future.result()
                    # Update in database
                    if db.insert_paper(enriched_paper):  # INSERT OR REPLACE
                        enriched += 1
                        print(f"  ✓ Enriched {enriched_paper.pmid or enriched_paper.doi}")
                except Exception as e:
                    print(f"  ✗ Error enriching: {e}")
    
    # Save to database
    for metadata in all_papers_final:
        if metadata is None:
            failed += 1
            continue
        
        openalex_success = metadata.openalex_retrieved if hasattr(metadata, 'openalex_retrieved') else False
        
        if db.insert_paper(metadata):
            processed += 1
            if metadata.is_full_text_pmc:
                with_fulltext += 1
            if openalex_success:
                with_openalex += 1
            
            # Track papers without full text
            if not metadata.is_full_text_pmc and metadata.doi:
                db.add_failed_doi(
                    metadata.doi,
                    metadata.pmid,
                    "No full text available",
                    datetime.now().isoformat()
                )
        else:
            failed += 1
    
    return processed, with_fulltext, with_openalex, failed, skipped, enriched


def collect_europepmc_papers(query: str, 
                             max_results: int = 5000, 
                             include_preprints: bool = True,
                             use_threading: bool = True, 
                             output_dir: str = None, 
                             query_description: str = None, 
                             query_id: int = None,
                             skip_existing: bool = True):
    """
    Main function to collect papers from Europe PMC.
    
    Args:
        query: Search query (supports Boolean operators)
        max_results: Maximum number of results to retrieve
        include_preprints: If True, includes preprints; if False, only peer-reviewed
        use_threading: Whether to use multi-threading
        output_dir: Custom output directory
        query_description: Optional description for the query
        query_id: Optional query ID
        skip_existing: If True, skip ALL papers already in database (no enrichment). Default: True
    """
    # Set custom output directory if provided
    if output_dir:
        from src.config import set_output_directory
        paths = set_output_directory(output_dir)
        print("\n" + "="*60)
        print("EUROPE PMC PAPER COLLECTION SYSTEM")
        print("="*60)
        print(f"Output directory: {paths['base_dir']}")
        print(f"Database: {paths['database_path']}")
        print("="*60 + "\n")
    else:
        print("\n" + "="*60)
        print("EUROPE PMC PAPER COLLECTION SYSTEM")
        print("="*60 + "\n")
    
    # Initialize statistics
    stats = CollectionStats(query=query)
    
    # Search Europe PMC
    print(f"Step 1: Searching Europe PMC...")
    paper_list = search_europepmc(query, max_results, include_preprints)
    
    if not paper_list:
        print("No papers found. Exiting.")
        return
    
    stats.total_found = len(paper_list)
    
    # Print statistics about found papers
    paper_stats = get_paper_statistics(paper_list)
    print(f"\nFound {stats.total_found} papers:")
    print(f"  - Published papers: {paper_stats['published']}")
    print(f"  - Preprints: {paper_stats['preprints']}")
    print(f"  - With PMC full text: {paper_stats['with_pmcid']}")
    print(f"  - Total citations: {paper_stats['total_citations']}\n")
    
    # Initialize database
    print("Step 2: Initializing database...")
    if output_dir:
        from src.config import DATABASE_PATH
        db = PaperDatabase(db_path=DATABASE_PATH)
    else:
        db = PaperDatabase()
    print(f"Database initialized at: {db.db_path}\n")
    
    # Create or use existing query_id
    if query_id is None:
        print("Step 2.1: Creating query record...")
        query_id = db.insert_query(query, query_description)
        print(f"Query registered with ID: {query_id}\n")
    else:
        print(f"Using existing query ID: {query_id}\n")
    
    # Process papers
    print("Step 3: Processing papers (extracting metadata and full text)...")
    print(f"Configuration: {NUM_THREADS} threads, batch size {BATCH_SIZE}")
    print(f"Checkpoints will be saved every {CHECKPOINT_EVERY} batches\n")
    
    start_time = time.time()
    total_skipped = 0
    
    if use_threading:
        # Multi-threaded processing
        batches = [paper_list[i:i+BATCH_SIZE] for i in range(0, len(paper_list), BATCH_SIZE)]
        
        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            futures = {executor.submit(process_batch, batch, db, query_id, skip_existing): batch for batch in batches}
            
            for i, future in enumerate(tqdm(as_completed(futures), total=len(futures), desc="Processing batches")):
                try:
                    processed, with_fulltext, with_openalex, failed, skipped, enriched = future.result()
                    stats.total_processed += processed
                    stats.with_full_text += with_fulltext
                    stats.with_openalex += with_openalex
                    stats.failed_pubmed += failed
                    total_skipped += skipped
                    # Note: enriched papers are included in total_processed
                    
                except Exception as exc:
                    print(f"\nBatch failed with exception: {exc}")
                    print(f"Full traceback:", file=sys.stderr)
                    traceback.print_exc(file=sys.stderr)
                    stats.failed_pubmed += len(futures[future])
                
                # Checkpoint
                if (i + 1) % CHECKPOINT_EVERY == 0 or (i + 1) == len(futures):
                    print(f"\n[Checkpoint {i+1}/{len(futures)}] Processed: {stats.total_processed}, "
                          f"With full text: {stats.with_full_text}, "
                          f"With OpenAlex: {stats.with_openalex}, "
                          f"Skipped (already in DB): {total_skipped}")
    else:
        # Single-threaded processing
        batches = [paper_list[i:i+BATCH_SIZE] for i in range(0, len(paper_list), BATCH_SIZE)]
        
        for batch in tqdm(batches, desc="Processing batches"):
            try:
                processed, with_fulltext, with_openalex, failed, skipped, enriched = process_batch(batch, db, query_id, skip_existing)
                stats.total_processed += processed
                stats.with_full_text += with_fulltext
                stats.with_openalex += with_openalex
                stats.failed_pubmed += failed
                total_skipped += skipped
                # Note: enriched papers are included in total_processed
            except Exception as exc:
                print(f"\nBatch failed with exception: {exc}")
                print(f"Full traceback:", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                stats.failed_pubmed += len(batch)
    
    elapsed = time.time() - start_time
    stats.end_time = datetime.now().isoformat()
    stats.without_full_text = stats.total_processed - stats.with_full_text
    
    print(f"\n\nProcessing completed in {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
    if total_skipped > 0:
        print(f"Skipped {total_skipped} papers (already in database)")
    
    # Save statistics
    print("\nStep 4: Saving results...")
    db.save_collection_stats(stats)
    
    # Export data
    json_path = db.export_to_json()
    failed_path = db.export_failed_dois_to_file(format='json')
    
    # Print final statistics
    stats.print_summary()
    
    print("Exported files:")
    print(f"  - All papers (JSON): {json_path}")
    print(f"  - Papers without full text: {failed_path}")
    print(f"  - Database: {db.db_path}")
    
    # Database statistics
    db_stats = db.get_statistics()
    print("\nDatabase statistics:")
    for key, value in db_stats.items():
        print(f"  - {key}: {value}")
    
    db.close()
    print("\n" + "="*60)
    print("Collection completed successfully!")
    print("="*60 + "\n")


def main():
    """Main entry point"""
    # Example: Search for aging papers (published + preprints)
    query = "aging AND senescence"
    
    # Parameters
    max_results = 1000
    include_preprints = True  # Set to False for published papers only
    use_threading = True
    output_dir = None  # Or specify: "europepmc_collection"
    
    try:
        collect_europepmc_papers(
            query=query,
            max_results=max_results,
            include_preprints=include_preprints,
            use_threading=use_threading,
            output_dir=output_dir,
            query_description=f"Europe PMC search: {query}"
        )
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user. Exiting...")
    except Exception as e:
        print(f"\n\nError in main execution: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
