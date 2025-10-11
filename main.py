#!/usr/bin/env python3
"""
Main orchestrator for PubMed paper collection system
"""
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from typing import List, Tuple, Optional

from src.models import PaperMetadata, CollectionStats
from src.pubmed_extractor import search_pubmed, search_pubmed_by_dois, process_paper, extract_pubmed_metadata_batch
from src.openalex_extractor import enrich_with_openalex
from src.database import PaperDatabase
from src.config import (
    NUM_THREADS, BATCH_SIZE, CHECKPOINT_EVERY,
    CHECKPOINT_DIR, FAILED_DOIS_FILE, METADATA_FETCH_BATCH_SIZE,
    FULLTEXT_PARALLEL_WORKERS, rotate_credentials, NCBI_CREDENTIALS
)


def process_paper_with_openalex(pmid: str) -> Tuple[Optional[PaperMetadata], bool, bool]:
    """
    Process a single paper: extract PubMed metadata, full text, and OpenAlex data.
    
    Args:
        pmid: PubMed ID
        
    Returns:
        Tuple of (metadata, pubmed_success, openalex_success)
    """
    # Extract PubMed metadata
    metadata = process_paper(pmid)
    if metadata is None:
        return None, False, False
    
    pubmed_success = True
    
    # Enrich with OpenAlex data
    openalex_success = False
    if metadata.doi:
        enriched_metadata = enrich_with_openalex(metadata)
        openalex_success = enriched_metadata.openalex_retrieved
        return enriched_metadata, pubmed_success, openalex_success
    
    return metadata, pubmed_success, openalex_success


def process_batch(pmid_batch: List[str], db: PaperDatabase) -> Tuple[int, int, int, int, int]:
    """
    Process a batch of PMIDs using batch metadata fetching for speed.
    
    Args:
        pmid_batch: List of PMIDs to process
        db: Database handler
        
    Returns:
        Tuple of (processed, with_fulltext, with_openalex, failed, skipped)
    """
    processed = 0
    with_fulltext = 0
    with_openalex = 0
    failed = 0
    skipped = 0
    
    # Filter out papers that already exist in database
    pmids_to_process = [pmid for pmid in pmid_batch if not db.paper_exists(pmid)]
    skipped = len(pmid_batch) - len(pmids_to_process)
    
    if not pmids_to_process:
        return processed, with_fulltext, with_openalex, failed, skipped
    
    # Batch fetch metadata for all PMIDs at once (much faster!)
    # Split into sub-batches if needed to respect METADATA_FETCH_BATCH_SIZE
    all_metadata = {}
    for i in range(0, len(pmids_to_process), METADATA_FETCH_BATCH_SIZE):
        sub_batch = pmids_to_process[i:i+METADATA_FETCH_BATCH_SIZE]
        batch_metadata = extract_pubmed_metadata_batch(sub_batch)
        all_metadata.update(batch_metadata)
    
    # Check for PMIDs that failed batch extraction and try individual extraction
    missing_pmids = [pmid for pmid in pmids_to_process if pmid not in all_metadata]
    if missing_pmids:
        print(f"\n⚠ Batch extraction failed for {len(missing_pmids)} PMIDs, trying individual extraction...")
        from src.pubmed_extractor import extract_pubmed_metadata
        for pmid in missing_pmids:
            individual_metadata = extract_pubmed_metadata(pmid)
            if individual_metadata:
                all_metadata[pmid] = individual_metadata
                print(f"  ✓ Successfully extracted PMID {pmid} individually")
            else:
                print(f"  ✗ Failed to extract PMID {pmid}")
                failed += 1
    
    # Now process each paper (fetch full text and OpenAlex data)
    # Note: PMC doesn't support batch full text retrieval, so we fetch individually
    # but we can parallelize within the batch using ThreadPoolExecutor
    from src.pubmed_extractor import try_all_fulltext_sources
    from concurrent.futures import ThreadPoolExecutor as FullTextExecutor
    
    def fetch_fulltext_for_paper(metadata):
        """Helper to fetch full text for a single paper"""
        full_text, sections = try_all_fulltext_sources(metadata)
        if full_text:
            metadata.full_text = full_text
            metadata.full_text_sections = sections
            metadata.is_full_text_pmc = True
        return metadata
    
    # Parallel full text fetching
    # Split papers: those with PMCIDs (direct fetch) vs those without (try DOI search)
    papers_with_pmcid = [all_metadata[pmid] for pmid in pmids_to_process 
                         if pmid in all_metadata and all_metadata[pmid].pmcid]
    papers_without_pmcid = [all_metadata[pmid] for pmid in pmids_to_process 
                           if pmid in all_metadata and not all_metadata[pmid].pmcid]
    
    # Fetch full texts in parallel for papers with PMCIDs (respects rate limiting in safe_ncbi_call)
    if papers_with_pmcid:
        with FullTextExecutor(max_workers=FULLTEXT_PARALLEL_WORKERS) as ft_executor:
            futures = {ft_executor.submit(fetch_fulltext_for_paper, paper): paper 
                      for paper in papers_with_pmcid}
            for future in futures:
                try:
                    future.result()  # Updates metadata in place
                except Exception as e:
                    print(f"Error fetching full text: {e}")
    
    # Also try to fetch full text for papers WITHOUT PMCIDs using DOI/other methods
    # This catches papers that are in PMC but PMCID wasn't in the initial metadata
    if papers_without_pmcid:
        with FullTextExecutor(max_workers=FULLTEXT_PARALLEL_WORKERS) as ft_executor:
            futures = {ft_executor.submit(fetch_fulltext_for_paper, paper): paper 
                      for paper in papers_without_pmcid}
            for future in futures:
                try:
                    future.result()  # Updates metadata in place
                except Exception as e:
                    print(f"Error fetching full text: {e}")
    
    # Process all papers (with and without full text)
    all_papers_to_save = papers_with_pmcid + papers_without_pmcid
    
    # Parallelize OpenAlex enrichment for papers with DOIs
    papers_with_doi = [m for m in all_papers_to_save if m and m.doi]
    papers_without_doi = [m for m in all_papers_to_save if m and not m.doi]
    
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
    
    # Combine enriched and non-enriched papers
    all_papers_final = enriched_papers + papers_without_doi
    
    for metadata in all_papers_final:
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
                    "No PMC full text available",
                    datetime.now().isoformat()
                )
        else:
            failed += 1
    
    return processed, with_fulltext, with_openalex, failed, skipped


def collect_papers(query: str, max_results: int = 50000, use_threading: bool = True, output_dir: str = None):
    """
    Main function to collect papers from PubMed.
    
    Args:
        query: PubMed search query
        max_results: Maximum number of results to retrieve
        use_threading: Whether to use multi-threading
        output_dir: Custom output directory (default: paper_collection/data)
                   Can be relative (to project root) or absolute path
    """
    # Set custom output directory if provided
    if output_dir:
        from src.config import set_output_directory
        paths = set_output_directory(output_dir)
        print("\n" + "="*60)
        print("PUBMED PAPER COLLECTION SYSTEM")
        print("="*60)
        print(f"Output directory: {paths['base_dir']}")
        print(f"Database: {paths['database_path']}")
        print("="*60 + "\n")
    else:
        print("\n" + "="*60)
        print("PUBMED PAPER COLLECTION SYSTEM")
        print("="*60 + "\n")
    
    # Initialize statistics
    stats = CollectionStats(query=query)
    
    # Search PubMed
    print("Step 1: Searching PubMed...")
    pmid_list = search_pubmed(query, max_results)
    
    if not pmid_list:
        print("No papers found. Exiting.")
        return
    
    stats.total_found = len(pmid_list)
    print(f"Found {stats.total_found} papers\n")
    
    # Initialize database
    print("Step 2: Initializing database...")
    if output_dir:
        # Use the updated DATABASE_PATH from config after set_output_directory was called
        from src.config import DATABASE_PATH
        db = PaperDatabase(db_path=DATABASE_PATH)
    else:
        db = PaperDatabase()
    print(f"Database initialized at: {db.db_path}\n")
    
    # Process papers
    print("Step 3: Processing papers (extracting metadata and full text)...")
    print(f"Configuration: {NUM_THREADS} threads, batch size {BATCH_SIZE}")
    print(f"Checkpoints will be saved every {CHECKPOINT_EVERY} batches\n")
    
    start_time = time.time()
    total_skipped = 0
    
    if use_threading:
        # Multi-threaded processing
        batches = [pmid_list[i:i+BATCH_SIZE] for i in range(0, len(pmid_list), BATCH_SIZE)]
        
        # Rotate credentials proactively every N batches to distribute load
        batches_per_credential = max(10, len(batches) // len(NCBI_CREDENTIALS))
        
        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            futures = {executor.submit(process_batch, batch, db): batch for batch in batches}
            
            for i, future in enumerate(tqdm(as_completed(futures), total=len(futures), desc="Processing batches")):
                try:
                    processed, with_fulltext, with_openalex, failed, skipped = future.result()
                    stats.total_processed += processed
                    stats.with_full_text += with_fulltext
                    stats.with_openalex += with_openalex
                    stats.failed_pubmed += failed
                    total_skipped += skipped
                    
                except Exception as exc:
                    print(f"\nBatch failed with exception: {exc}")
                    stats.failed_pubmed += len(futures[future])
                
                # Proactively rotate credentials every N batches
                if (i + 1) % batches_per_credential == 0 and (i + 1) < len(futures):
                    print(f"\n[Proactive rotation] Switching credentials after {i+1} batches")
                    rotate_credentials()
                
                # Checkpoint
                if (i + 1) % CHECKPOINT_EVERY == 0 or (i + 1) == len(futures):
                    print(f"\n[Checkpoint {i+1}/{len(futures)}] Processed: {stats.total_processed}, "
                          f"With full text: {stats.with_full_text}, "
                          f"With OpenAlex: {stats.with_openalex}, "
                          f"Skipped (already in DB): {total_skipped}")
    else:
        # Single-threaded processing (for debugging)
        for i, pmid in enumerate(tqdm(pmid_list, desc="Processing papers")):
            # Skip if paper already exists in database
            if db.paper_exists(pmid):
                total_skipped += 1
                continue
            
            metadata, pubmed_success, openalex_success = process_paper_with_openalex(pmid)
            
            if metadata:
                if db.insert_paper(metadata):
                    stats.total_processed += 1
                    if metadata.is_full_text_pmc:
                        stats.with_full_text += 1
                    if openalex_success:
                        stats.with_openalex += 1
                    
                    if not metadata.is_full_text_pmc and metadata.doi:
                        db.add_failed_doi(
                            metadata.doi,
                            metadata.pmid,
                            "No PMC full text available",
                            datetime.now().isoformat()
                        )
            else:
                stats.failed_pubmed += 1
    
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
    failed_path = db.export_failed_dois_to_file(format='json')  # Export as JSON
    
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


def collect_papers_from_dois(dois: List[str], use_threading: bool = True, output_dir: str = None):
    """
    Collect papers from a list of DOIs.
    
    Args:
        dois: List of DOIs
        use_threading: Whether to use multi-threading
        output_dir: Custom output directory (default: paper_collection/data)
    """
    # Set custom output directory if provided
    if output_dir:
        from src.config import set_output_directory
        paths = set_output_directory(output_dir)
        print("\n" + "="*60)
        print("PUBMED PAPER COLLECTION SYSTEM (FROM DOIs)")
        print("="*60)
        print(f"Output directory: {paths['base_dir']}")
        print(f"Database: {paths['database_path']}")
        print("="*60 + "\n")
    else:
        print("\n" + "="*60)
        print("PUBMED PAPER COLLECTION SYSTEM (FROM DOIs)")
        print("="*60 + "\n")
    
    # Initialize statistics
    stats = CollectionStats(query=f"DOI list ({len(dois)} DOIs)")
    
    # Search PubMed for DOIs to get PMIDs
    print("Step 1: Searching PubMed for DOIs...")
    doi_to_pmid = search_pubmed_by_dois(dois)
    
    if not doi_to_pmid:
        print("No papers found in PubMed. Exiting.")
        return
    
    pmid_list = list(doi_to_pmid.values())
    stats.total_found = len(pmid_list)
    print(f"\nFound {stats.total_found} papers in PubMed\n")
    
    # Initialize database
    print("Step 2: Initializing database...")
    if output_dir:
        # Use the updated DATABASE_PATH from config after set_output_directory was called
        from src.config import DATABASE_PATH
        db = PaperDatabase(db_path=DATABASE_PATH)
    else:
        db = PaperDatabase()
    print(f"Database initialized at: {db.db_path}\n")
    
    # Process papers
    print("Step 3: Processing papers (extracting metadata and full text)...")
    print(f"Configuration: {NUM_THREADS} threads, batch size {BATCH_SIZE}")
    print(f"Checkpoints will be saved every {CHECKPOINT_EVERY} batches\n")
    
    start_time = time.time()
    total_skipped = 0
    
    if use_threading:
        # Multi-threaded processing
        batches = [pmid_list[i:i+BATCH_SIZE] for i in range(0, len(pmid_list), BATCH_SIZE)]
        
        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            futures = {executor.submit(process_batch, batch, db): batch for batch in batches}
            
            for i, future in enumerate(tqdm(as_completed(futures), total=len(futures), desc="Processing batches")):
                try:
                    processed, with_fulltext, with_openalex, failed, skipped = future.result()
                    stats.total_processed += processed
                    stats.with_full_text += with_fulltext
                    stats.with_openalex += with_openalex
                    stats.failed_pubmed += failed
                    total_skipped += skipped
                    
                except Exception as exc:
                    print(f"\nBatch failed with exception: {exc}")
                    stats.failed_pubmed += len(futures[future])
    else:
        # Single-threaded processing
        batches = [pmid_list[i:i+BATCH_SIZE] for i in range(0, len(pmid_list), BATCH_SIZE)]
        
        for batch in tqdm(batches, desc="Processing batches"):
            try:
                processed, with_fulltext, with_openalex, failed, skipped = process_batch(batch, db)
                stats.total_processed += processed
                stats.with_full_text += with_fulltext
                stats.with_openalex += with_openalex
                stats.failed_pubmed += failed
                total_skipped += skipped
            except Exception as exc:
                print(f"\nBatch failed with exception: {exc}")
                stats.failed_pubmed += len(batch)
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    stats.elapsed_time = elapsed_time
    
    print(f"\n\nProcessing completed in {elapsed_time:.2f} seconds")
    print(f"Skipped {total_skipped} papers already in database")
    
    # Save statistics
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
    # Example query from user requirements
    query = """
    (
      (
        aging[Title] OR ageing[Title] 
      )
      AND
      (
        theory[Title] OR theories[Title] OR hypothesis[Title] OR hypotheses[Title] OR paradigm[Title] OR paradigms[Title]
      )
      OR ("theory of aging"[TI] OR "theory of ageing")
    )
    NOT
    (
      Case Reports[Publication Type] OR "case report"[Title] OR "case reports"[Title] OR Clinical Trial[Publication Type] OR "protocol"[Title] OR "conference"[Title] OR "meeting"[Title] OR "healthy aging"[TI] OR "healthy ageing"[TI] OR "well-being"[TI] OR "successful aging"[TI] OR "successful ageing"[TI] OR "normal ageing"[TI] OR "normal aging"[TI] OR "ovarian"[TI] OR "liver"[TI] OR "kidne*"[TI] OR "skin"[TI] OR "religion"[TI] OR "enjoyment"[TI] OR "disease hypothesis"[TI] OR "biological aging"[TI] OR "biological ageing"[TI] 
    )
    """
    
    # You can modify these parameters
    max_results = 50000  # Maximum number of papers to retrieve
    use_threading = True  # Set to False for debugging
    
    try:
        collect_papers(query, max_results, use_threading)
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user. Exiting...")
    except Exception as e:
        print(f"\n\nError in main execution: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
