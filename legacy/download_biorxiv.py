#!/usr/bin/env python3
"""
Main orchestrator for bioRxiv/medRxiv paper collection system
"""
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from typing import List, Tuple, Optional

from src.models import PaperMetadata, CollectionStats
from src.biorxiv_extractor import (
    search_biorxiv, process_biorxiv_paper, 
    extract_biorxiv_metadata, try_biorxiv_fulltext
)
from src.openalex_extractor import enrich_with_openalex
from src.database import PaperDatabase
from src.config import NUM_THREADS, BATCH_SIZE, CHECKPOINT_EVERY


def process_paper_with_openalex(paper_dict: dict) -> Tuple[Optional[PaperMetadata], bool, bool]:
    """
    Process a single paper: extract bioRxiv metadata, full text, and OpenAlex data.
    
    Args:
        paper_dict: Paper dictionary from bioRxiv API
        
    Returns:
        Tuple of (metadata, biorxiv_success, openalex_success)
    """
    # Extract bioRxiv metadata
    metadata = extract_biorxiv_metadata(paper_dict)
    if metadata is None:
        return None, False, False
    
    biorxiv_success = True
    
    # Try to get full text
    full_text, sections = try_biorxiv_fulltext(metadata)
    if full_text:
        metadata.full_text = full_text
        metadata.full_text_sections = sections
        metadata.is_full_text_pmc = True
    
    # Enrich with OpenAlex data
    openalex_success = False
    if metadata.doi:
        enriched_metadata = enrich_with_openalex(metadata)
        openalex_success = enriched_metadata.openalex_retrieved
        return enriched_metadata, biorxiv_success, openalex_success
    
    return metadata, biorxiv_success, openalex_success


def process_batch(paper_batch: List[dict], db: PaperDatabase, query_id: int = None) -> Tuple[int, int, int, int, int]:
    """
    Process a batch of papers.
    
    Args:
        paper_batch: List of paper dictionaries from bioRxiv API
        db: Database handler
        query_id: Query ID to assign to papers
        
    Returns:
        Tuple of (processed, with_fulltext, with_openalex, failed, skipped)
    """
    processed = 0
    with_fulltext = 0
    with_openalex = 0
    failed = 0
    skipped = 0
    
    # Filter out papers that already exist in database (by DOI)
    papers_to_process = []
    for paper in paper_batch:
        doi = paper.get('doi')
        if doi and not db.paper_exists(doi):
            papers_to_process.append(paper)
        else:
            skipped += 1
    
    if not papers_to_process:
        return processed, with_fulltext, with_openalex, failed, skipped
    
    # Process each paper
    all_metadata = []
    for paper in papers_to_process:
        metadata = extract_biorxiv_metadata(paper)
        if metadata:
            all_metadata.append(metadata)
        else:
            failed += 1
    
    # Parallel full text fetching
    from concurrent.futures import ThreadPoolExecutor as FullTextExecutor
    
    def fetch_fulltext_for_paper(metadata):
        """Helper to fetch full text for a single paper"""
        full_text, sections = try_biorxiv_fulltext(metadata)
        if full_text:
            metadata.full_text = full_text
            metadata.full_text_sections = sections
            metadata.is_full_text_pmc = True
        return metadata
    
    if all_metadata:
        with FullTextExecutor(max_workers=min(2, len(all_metadata))) as ft_executor:
            futures = {ft_executor.submit(fetch_fulltext_for_paper, paper): paper 
                      for paper in all_metadata}
            for future in futures:
                try:
                    future.result()  # Updates metadata in place
                except Exception as e:
                    print(f"Error fetching full text: {e}")
    
    # Assign query_id to all metadata objects if provided
    if query_id is not None:
        for metadata in all_metadata:
            if metadata:
                metadata.query_id = query_id
    
    # Parallelize OpenAlex enrichment for papers with DOIs
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
                    enriched_papers.append(futures[future])  # Use original if enrichment fails
    else:
        enriched_papers = []
    
    # Save all papers to database
    for metadata in enriched_papers:
        if metadata is None:
            failed += 1
            continue
        
        openalex_success = metadata.openalex_retrieved if hasattr(metadata, 'openalex_retrieved') else False
        
        # Save to database
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
                    "No bioRxiv full text available",
                    datetime.now().isoformat()
                )
        else:
            failed += 1
    
    return processed, with_fulltext, with_openalex, failed, skipped


def collect_biorxiv_papers(query: str, max_results: int = 5000, 
                           use_threading: bool = True, 
                           output_dir: str = None, 
                           query_description: str = None, 
                           query_id: int = None,
                           server: str = "biorxiv"):
    """
    Main function to collect papers from bioRxiv/medRxiv.
    
    Args:
        query: Search query (keywords to filter by)
        max_results: Maximum number of results to retrieve
        use_threading: Whether to use multi-threading
        output_dir: Custom output directory (default: paper_collection/data)
        query_description: Optional description for the query
        query_id: Optional query ID (if None, a new query will be created in the database)
        server: 'biorxiv' or 'medrxiv'
    """
    # Set custom output directory if provided
    if output_dir:
        from src.config import set_output_directory
        paths = set_output_directory(output_dir)
        print("\n" + "="*60)
        print(f"{server.upper()} PAPER COLLECTION SYSTEM")
        print("="*60)
        print(f"Output directory: {paths['base_dir']}")
        print(f"Database: {paths['database_path']}")
        print("="*60 + "\n")
    else:
        print("\n" + "="*60)
        print(f"{server.upper()} PAPER COLLECTION SYSTEM")
        print("="*60 + "\n")
    
    # Initialize statistics
    stats = CollectionStats(query=query)
    
    # Search bioRxiv
    print(f"Step 1: Searching {server}...")
    paper_list = search_biorxiv(query, max_results, server=server)
    
    if not paper_list:
        print("No papers found. Exiting.")
        return
    
    stats.total_found = len(paper_list)
    print(f"Found {stats.total_found} papers\n")
    
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
            futures = {executor.submit(process_batch, batch, db, query_id): batch for batch in batches}
            
            for i, future in enumerate(tqdm(as_completed(futures), total=len(futures), desc="Processing batches")):
                try:
                    processed, with_fulltext, with_openalex, failed, skipped = future.result()
                    stats.total_processed += processed
                    stats.with_full_text += with_fulltext
                    stats.with_openalex += with_openalex
                    stats.failed_pubmed += failed  # Reusing field name
                    total_skipped += skipped
                    
                except Exception as exc:
                    print(f"\nBatch failed with exception: {exc}")
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
                processed, with_fulltext, with_openalex, failed, skipped = process_batch(batch, db, query_id)
                stats.total_processed += processed
                stats.with_full_text += with_fulltext
                stats.with_openalex += with_openalex
                stats.failed_pubmed += failed
                total_skipped += skipped
            except Exception as exc:
                print(f"\nBatch failed with exception: {exc}")
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
    # Example query
    query = "aging theory"  # Keywords to search for in title/abstract
    
    # You can modify these parameters
    max_results = 1000  # Maximum number of papers to retrieve
    use_threading = True  # Set to False for debugging
    server = "biorxiv"  # or "medrxiv"
    
    # Optional: specify custom output directory
    # output_dir = "biorxiv_collection"
    output_dir = None
    
    try:
        collect_biorxiv_papers(
            query=query,
            max_results=max_results,
            use_threading=use_threading,
            output_dir=output_dir,
            query_description=f"bioRxiv papers about {query}",
            server=server
        )
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user. Exiting...")
    except Exception as e:
        print(f"\n\nError in main execution: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
