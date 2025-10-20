#!/usr/bin/env python3
"""
Paper collection script that saves directly to JSON files (no database)
Output directory: ./individual_runs
"""
import sys
import os
import json
from datetime import datetime
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from typing import List, Tuple, Optional

from src.models import PaperMetadata, CollectionStats
from src.pubmed_extractor import search_pubmed, search_pubmed_by_dois, extract_pubmed_metadata_batch
from src.openalex_extractor import enrich_with_openalex
from src.config import (
    NUM_THREADS, BATCH_SIZE, CHECKPOINT_EVERY,
    METADATA_FETCH_BATCH_SIZE, FULLTEXT_PARALLEL_WORKERS
)

# ============================================================================
# LOGGING SETUP - Save all output to file
# ============================================================================

class TeeOutput:
    """Capture stdout/stderr and write to both console and file"""
    def __init__(self, file_path, original_stream):
        self.file = open(file_path, 'w', buffering=1)  # Line buffered
        self.original_stream = original_stream
    
    def write(self, message):
        self.original_stream.write(message)
        self.file.write(message)
    
    def flush(self):
        self.original_stream.flush()
        self.file.flush()
    
    def close(self):
        self.file.close()


def process_batch_to_json(pmid_batch: List[str], existing_pmids: set) -> Tuple[List[PaperMetadata], int]:
    """
    Process a batch of PMIDs and return metadata objects (no database storage).
    
    Args:
        pmid_batch: List of PMIDs to process
        existing_pmids: Set of PMIDs already processed (to skip duplicates)
        
    Returns:
        Tuple of (list of metadata objects, skipped count)
    """
    # Filter out papers that already exist
    pmids_to_process = [pmid for pmid in pmid_batch if pmid not in existing_pmids]
    skipped = len(pmid_batch) - len(pmids_to_process)
    
    if not pmids_to_process:
        return [], skipped
    
    # Batch fetch metadata for all PMIDs at once
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
    
    # Fetch full text for all papers
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
    
    # Split papers: those with PMCIDs vs those without
    papers_with_pmcid = [all_metadata[pmid] for pmid in pmids_to_process 
                         if pmid in all_metadata and all_metadata[pmid].pmcid]
    papers_without_pmcid = [all_metadata[pmid] for pmid in pmids_to_process 
                           if pmid in all_metadata and not all_metadata[pmid].pmcid]
    
    # Fetch full texts in parallel
    if papers_with_pmcid:
        with FullTextExecutor(max_workers=FULLTEXT_PARALLEL_WORKERS) as ft_executor:
            futures = {ft_executor.submit(fetch_fulltext_for_paper, paper): paper 
                      for paper in papers_with_pmcid}
            for future in futures:
                try:
                    future.result()  # Updates metadata in place
                except Exception as e:
                    print(f"Error fetching full text: {e}")
    
    # Also try to fetch full text for papers WITHOUT PMCIDs
    if papers_without_pmcid:
        with FullTextExecutor(max_workers=FULLTEXT_PARALLEL_WORKERS) as ft_executor:
            futures = {ft_executor.submit(fetch_fulltext_for_paper, paper): paper 
                      for paper in papers_without_pmcid}
            for future in futures:
                try:
                    future.result()  # Updates metadata in place
                except Exception as e:
                    print(f"Error fetching full text: {e}")
    
    # Combine all papers
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
    
    return [m for m in all_papers_final if m is not None], skipped


def collect_papers_to_json(query: str, max_results: int = 50000, use_threading: bool = True, 
                           query_description: str = None, run_name: str = None):
    """
    Main function to collect papers from PubMed and save directly to JSON.
    
    Args:
        query: PubMed search query
        max_results: Maximum number of results to retrieve
        use_threading: Whether to use multi-threading
        query_description: Optional description for the query
        run_name: Optional name for this collection run (used in filenames)
    """
    # Create output directory
    output_base = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "individual_runs"
    output_base.mkdir(exist_ok=True)
    
    # Create timestamp-based subdirectory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if run_name:
        run_dir = output_base / f"{run_name}_{timestamp}"
    else:
        run_dir = output_base / f"collection_{timestamp}"
    run_dir.mkdir(exist_ok=True)
    
    # Setup logging
    log_file = run_dir / "collection.log"
    stdout_tee = TeeOutput(log_file, sys.stdout)
    sys.stdout = stdout_tee
    
    print("="*80)
    print("PUBMED PAPER COLLECTION TO JSON")
    print("="*80)
    print(f"Output directory: {run_dir}")
    print(f"Log file: {log_file}")
    print("="*80 + "\n")
    
    # Initialize statistics
    stats = CollectionStats(query=query)
    stats.start_time = datetime.now().isoformat()
    
    # Save query information
    query_info = {
        "query": query,
        "description": query_description,
        "max_results": max_results,
        "timestamp": timestamp,
        "run_name": run_name
    }
    with open(run_dir / "query_info.json", 'w', encoding='utf-8') as f:
        json.dump(query_info, f, indent=2, ensure_ascii=False)
    
    # Search PubMed
    print("Step 1: Searching PubMed...")
    pmid_list = search_pubmed(query, max_results)
    
    if not pmid_list:
        print("No papers found. Exiting.")
        stdout_tee.close()
        return
    
    stats.total_found = len(pmid_list)
    print(f"Found {stats.total_found} papers\n")
    
    # Save PMID list
    with open(run_dir / "pmid_list.json", 'w', encoding='utf-8') as f:
        json.dump({
            "total": len(pmid_list),
            "pmids": pmid_list
        }, f, indent=2)
    
    # Process papers
    print("Step 2: Processing papers (extracting metadata and full text)...")
    print(f"Configuration: {NUM_THREADS} threads, batch size {BATCH_SIZE}")
    print(f"Checkpoints will be saved every {CHECKPOINT_EVERY} batches\n")
    
    start_time = time.time()
    total_skipped = 0
    all_papers = []
    existing_pmids = set()
    
    if use_threading:
        # Multi-threaded processing
        batches = [pmid_list[i:i+BATCH_SIZE] for i in range(0, len(pmid_list), BATCH_SIZE)]
        
        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            futures = {executor.submit(process_batch_to_json, batch, existing_pmids): batch 
                      for batch in batches}
            
            for i, future in enumerate(tqdm(as_completed(futures), total=len(futures), 
                                           desc="Processing batches")):
                try:
                    batch_papers, skipped = future.result()
                    all_papers.extend(batch_papers)
                    total_skipped += skipped
                    
                    # Update existing PMIDs to prevent duplicates
                    existing_pmids.update([p.pmid for p in batch_papers])
                    
                    # Count stats
                    for paper in batch_papers:
                        stats.total_processed += 1
                        if paper.is_full_text_pmc:
                            stats.with_full_text += 1
                        if paper.openalex_retrieved:
                            stats.with_openalex += 1
                    
                except Exception as exc:
                    print(f"\nBatch failed with exception: {exc}")
                    stats.failed_pubmed += len(futures[future])
                
                # Checkpoint - save intermediate results
                if (i + 1) % CHECKPOINT_EVERY == 0 or (i + 1) == len(futures):
                    print(f"\n[Checkpoint {i+1}/{len(futures)}] Processed: {stats.total_processed}, "
                          f"With full text: {stats.with_full_text}, "
                          f"With OpenAlex: {stats.with_openalex}")
                    
                    # Save checkpoint file
                    checkpoint_file = run_dir / f"papers_checkpoint_{i+1}.json"
                    with open(checkpoint_file, 'w', encoding='utf-8') as f:
                        json.dump([p.to_dict() for p in all_papers], f, indent=2, ensure_ascii=False)
                    print(f"  Checkpoint saved to: {checkpoint_file}")
    else:
        # Single-threaded processing (for debugging)
        batches = [pmid_list[i:i+BATCH_SIZE] for i in range(0, len(pmid_list), BATCH_SIZE)]
        
        for i, batch in enumerate(tqdm(batches, desc="Processing batches")):
            try:
                batch_papers, skipped = process_batch_to_json(batch, existing_pmids)
                all_papers.extend(batch_papers)
                total_skipped += skipped
                
                # Update existing PMIDs
                existing_pmids.update([p.pmid for p in batch_papers])
                
                # Count stats
                for paper in batch_papers:
                    stats.total_processed += 1
                    if paper.is_full_text_pmc:
                        stats.with_full_text += 1
                    if paper.openalex_retrieved:
                        stats.with_openalex += 1
                
            except Exception as exc:
                print(f"\nBatch failed with exception: {exc}")
                stats.failed_pubmed += len(batch)
    
    elapsed = time.time() - start_time
    stats.end_time = datetime.now().isoformat()
    stats.without_full_text = stats.total_processed - stats.with_full_text
    
    print(f"\n\nProcessing completed in {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
    if total_skipped > 0:
        print(f"Skipped {total_skipped} duplicate papers")
    
    # Save final results
    print("\nStep 3: Saving results...")
    
    # Save all papers to JSON
    papers_file = run_dir / "papers_all.json"
    with open(papers_file, 'w', encoding='utf-8') as f:
        json.dump([p.to_dict() for p in all_papers], f, indent=2, ensure_ascii=False)
    print(f"  All papers saved to: {papers_file}")
    
    # Save papers with full text
    papers_with_fulltext = [p for p in all_papers if p.is_full_text_pmc]
    fulltext_file = run_dir / "papers_with_fulltext.json"
    with open(fulltext_file, 'w', encoding='utf-8') as f:
        json.dump([p.to_dict() for p in papers_with_fulltext], f, indent=2, ensure_ascii=False)
    print(f"  Papers with full text saved to: {fulltext_file}")
    
    # Save papers without full text
    papers_without_fulltext = [p for p in all_papers if not p.is_full_text_pmc]
    no_fulltext_file = run_dir / "papers_without_fulltext.json"
    with open(no_fulltext_file, 'w', encoding='utf-8') as f:
        json.dump([p.to_dict() for p in papers_without_fulltext], f, indent=2, ensure_ascii=False)
    print(f"  Papers without full text saved to: {no_fulltext_file}")
    
    # Save statistics
    stats_dict = {
        "query": stats.query,
        "total_found": stats.total_found,
        "total_processed": stats.total_processed,
        "with_full_text": stats.with_full_text,
        "without_full_text": stats.without_full_text,
        "with_openalex": stats.with_openalex,
        "failed_pubmed": stats.failed_pubmed,
        "start_time": stats.start_time,
        "end_time": stats.end_time,
        "elapsed_seconds": elapsed,
        "elapsed_minutes": elapsed / 60
    }
    stats_file = run_dir / "statistics.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats_dict, f, indent=2, ensure_ascii=False)
    print(f"  Statistics saved to: {stats_file}")
    
    # Print final statistics
    print("\n" + "="*80)
    print("COLLECTION SUMMARY")
    print("="*80)
    print(f"Total papers found:       {stats.total_found:,}")
    print(f"Successfully processed:   {stats.total_processed:,}")
    print(f"With PMC full text:       {stats.with_full_text:,} ({stats.with_full_text/stats.total_processed*100:.1f}%)")
    print(f"Without full text:        {stats.without_full_text:,} ({stats.without_full_text/stats.total_processed*100:.1f}%)")
    print(f"With OpenAlex data:       {stats.with_openalex:,} ({stats.with_openalex/stats.total_processed*100:.1f}%)")
    print(f"Failed:                   {stats.failed_pubmed:,}")
    print(f"Processing time:          {elapsed:.2f}s ({elapsed/60:.2f} min)")
    print("="*80)
    
    print("\nOutput files:")
    print(f"  - All papers:               {papers_file}")
    print(f"  - Papers with full text:    {fulltext_file}")
    print(f"  - Papers without full text: {no_fulltext_file}")
    print(f"  - Statistics:               {stats_file}")
    print(f"  - Query info:               {run_dir / 'query_info.json'}")
    print(f"  - PMID list:                {run_dir / 'pmid_list.json'}")
    print(f"  - Log file:                 {log_file}")
    
    print("\n" + "="*80)
    print("Collection completed successfully!")
    print("="*80 + "\n")
    
    # Close logging
    stdout_tee.close()


def collect_papers_from_dois_to_json(dois: List[str], use_threading: bool = True, 
                                      query_description: str = None, run_name: str = None):
    """
    Collect papers from a list of DOIs and save directly to JSON.
    
    Args:
        dois: List of DOIs to collect
        use_threading: Whether to use multi-threading
        query_description: Optional description for the collection
        run_name: Optional name for this collection run (used in filenames)
    """
    # Create output directory
    output_base = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "individual_runs"
    output_base.mkdir(exist_ok=True)
    
    # Create timestamp-based subdirectory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if run_name:
        run_dir = output_base / f"{run_name}_{timestamp}"
    else:
        run_dir = output_base / f"collection_dois_{timestamp}"
    run_dir.mkdir(exist_ok=True)
    
    # Setup logging
    log_file = run_dir / "collection.log"
    stdout_tee = TeeOutput(log_file, sys.stdout)
    sys.stdout = stdout_tee
    
    print("="*80)
    print("PUBMED PAPER COLLECTION FROM DOIs TO JSON")
    print("="*80)
    print(f"Output directory: {run_dir}")
    print(f"Log file: {log_file}")
    print("="*80 + "\n")
    
    # Initialize statistics
    stats = CollectionStats(query=f"DOI list ({len(dois)} DOIs)")
    stats.start_time = datetime.now().isoformat()
    
    # Save DOI list
    doi_info = {
        "total_dois": len(dois),
        "dois": dois,
        "description": query_description,
        "timestamp": timestamp,
        "run_name": run_name
    }
    with open(run_dir / "doi_list.json", 'w', encoding='utf-8') as f:
        json.dump(doi_info, f, indent=2, ensure_ascii=False)
    
    # Search PubMed for DOIs to get PMIDs
    print("Step 1: Searching PubMed for DOIs...")
    doi_to_pmid = search_pubmed_by_dois(dois)
    
    if not doi_to_pmid:
        print("No papers found in PubMed. Exiting.")
        stdout_tee.close()
        return
    
    pmid_list = list(doi_to_pmid.values())
    stats.total_found = len(pmid_list)
    print(f"\nFound {stats.total_found} papers in PubMed (out of {len(dois)} DOIs)\n")
    
    # Save DOI to PMID mapping
    with open(run_dir / "doi_to_pmid_mapping.json", 'w', encoding='utf-8') as f:
        json.dump({
            "found": len(doi_to_pmid),
            "not_found": len(dois) - len(doi_to_pmid),
            "mapping": doi_to_pmid
        }, f, indent=2, ensure_ascii=False)
    
    # Save PMID list
    with open(run_dir / "pmid_list.json", 'w', encoding='utf-8') as f:
        json.dump({
            "total": len(pmid_list),
            "pmids": pmid_list
        }, f, indent=2)
    
    # Process papers
    print("Step 2: Processing papers (extracting metadata and full text)...")
    print(f"Configuration: {NUM_THREADS} threads, batch size {BATCH_SIZE}")
    print(f"Checkpoints will be saved every {CHECKPOINT_EVERY} batches\n")
    
    start_time = time.time()
    total_skipped = 0
    all_papers = []
    existing_pmids = set()
    
    if use_threading:
        # Multi-threaded processing
        batches = [pmid_list[i:i+BATCH_SIZE] for i in range(0, len(pmid_list), BATCH_SIZE)]
        
        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            futures = {executor.submit(process_batch_to_json, batch, existing_pmids): batch 
                      for batch in batches}
            
            for i, future in enumerate(tqdm(as_completed(futures), total=len(futures), 
                                           desc="Processing batches")):
                try:
                    batch_papers, skipped = future.result()
                    all_papers.extend(batch_papers)
                    total_skipped += skipped
                    
                    # Update existing PMIDs to prevent duplicates
                    existing_pmids.update([p.pmid for p in batch_papers])
                    
                    # Count stats
                    for paper in batch_papers:
                        stats.total_processed += 1
                        if paper.is_full_text_pmc:
                            stats.with_full_text += 1
                        if paper.openalex_retrieved:
                            stats.with_openalex += 1
                    
                except Exception as exc:
                    print(f"\nBatch failed with exception: {exc}")
                    stats.failed_pubmed += len(futures[future])
                
                # Checkpoint - save intermediate results
                if (i + 1) % CHECKPOINT_EVERY == 0 or (i + 1) == len(futures):
                    print(f"\n[Checkpoint {i+1}/{len(futures)}] Processed: {stats.total_processed}, "
                          f"With full text: {stats.with_full_text}, "
                          f"With OpenAlex: {stats.with_openalex}")
                    
                    # Save checkpoint file
                    checkpoint_file = run_dir / f"papers_checkpoint_{i+1}.json"
                    with open(checkpoint_file, 'w', encoding='utf-8') as f:
                        json.dump([p.to_dict() for p in all_papers], f, indent=2, ensure_ascii=False)
                    print(f"  Checkpoint saved to: {checkpoint_file}")
    else:
        # Single-threaded processing (for debugging)
        batches = [pmid_list[i:i+BATCH_SIZE] for i in range(0, len(pmid_list), BATCH_SIZE)]
        
        for i, batch in enumerate(tqdm(batches, desc="Processing batches")):
            try:
                batch_papers, skipped = process_batch_to_json(batch, existing_pmids)
                all_papers.extend(batch_papers)
                total_skipped += skipped
                
                # Update existing PMIDs
                existing_pmids.update([p.pmid for p in batch_papers])
                
                # Count stats
                for paper in batch_papers:
                    stats.total_processed += 1
                    if paper.is_full_text_pmc:
                        stats.with_full_text += 1
                    if paper.openalex_retrieved:
                        stats.with_openalex += 1
                
            except Exception as exc:
                print(f"\nBatch failed with exception: {exc}")
                stats.failed_pubmed += len(batch)
    
    elapsed = time.time() - start_time
    stats.end_time = datetime.now().isoformat()
    stats.without_full_text = stats.total_processed - stats.with_full_text
    
    print(f"\n\nProcessing completed in {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
    if total_skipped > 0:
        print(f"Skipped {total_skipped} duplicate papers")
    
    # Save final results
    print("\nStep 3: Saving results...")
    
    # Save all papers to JSON
    papers_file = run_dir / "papers_all.json"
    with open(papers_file, 'w', encoding='utf-8') as f:
        json.dump([p.to_dict() for p in all_papers], f, indent=2, ensure_ascii=False)
    print(f"  All papers saved to: {papers_file}")
    
    # Save papers with full text
    papers_with_fulltext = [p for p in all_papers if p.is_full_text_pmc]
    fulltext_file = run_dir / "papers_with_fulltext.json"
    with open(fulltext_file, 'w', encoding='utf-8') as f:
        json.dump([p.to_dict() for p in papers_with_fulltext], f, indent=2, ensure_ascii=False)
    print(f"  Papers with full text saved to: {fulltext_file}")
    
    # Save papers without full text
    papers_without_fulltext = [p for p in all_papers if not p.is_full_text_pmc]
    no_fulltext_file = run_dir / "papers_without_fulltext.json"
    with open(no_fulltext_file, 'w', encoding='utf-8') as f:
        json.dump([p.to_dict() for p in papers_without_fulltext], f, indent=2, ensure_ascii=False)
    print(f"  Papers without full text saved to: {no_fulltext_file}")
    
    # Save statistics
    stats_dict = {
        "source": "DOI list",
        "total_dois_provided": len(dois),
        "dois_found_in_pubmed": len(doi_to_pmid),
        "dois_not_found": len(dois) - len(doi_to_pmid),
        "total_found": stats.total_found,
        "total_processed": stats.total_processed,
        "with_full_text": stats.with_full_text,
        "without_full_text": stats.without_full_text,
        "with_openalex": stats.with_openalex,
        "failed_pubmed": stats.failed_pubmed,
        "start_time": stats.start_time,
        "end_time": stats.end_time,
        "elapsed_seconds": elapsed,
        "elapsed_minutes": elapsed / 60
    }
    stats_file = run_dir / "statistics.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats_dict, f, indent=2, ensure_ascii=False)
    print(f"  Statistics saved to: {stats_file}")
    
    # Print final statistics
    print("\n" + "="*80)
    print("COLLECTION SUMMARY")
    print("="*80)
    print(f"DOIs provided:            {len(dois):,}")
    print(f"DOIs found in PubMed:     {len(doi_to_pmid):,}")
    print(f"DOIs not found:           {len(dois) - len(doi_to_pmid):,}")
    print(f"Papers processed:         {stats.total_processed:,}")
    print(f"With PMC full text:       {stats.with_full_text:,} ({stats.with_full_text/stats.total_processed*100:.1f}%)" if stats.total_processed > 0 else "With PMC full text:       0")
    print(f"Without full text:        {stats.without_full_text:,} ({stats.without_full_text/stats.total_processed*100:.1f}%)" if stats.total_processed > 0 else "Without full text:        0")
    print(f"With OpenAlex data:       {stats.with_openalex:,} ({stats.with_openalex/stats.total_processed*100:.1f}%)" if stats.total_processed > 0 else "With OpenAlex data:       0")
    print(f"Failed:                   {stats.failed_pubmed:,}")
    print(f"Processing time:          {elapsed:.2f}s ({elapsed/60:.2f} min)")
    print("="*80)
    
    print("\nOutput files:")
    print(f"  - All papers:               {papers_file}")
    print(f"  - Papers with full text:    {fulltext_file}")
    print(f"  - Papers without full text: {no_fulltext_file}")
    print(f"  - Statistics:               {stats_file}")
    print(f"  - DOI list:                 {run_dir / 'doi_list.json'}")
    print(f"  - DOI to PMID mapping:      {run_dir / 'doi_to_pmid_mapping.json'}")
    print(f"  - PMID list:                {run_dir / 'pmid_list.json'}")
    print(f"  - Log file:                 {log_file}")
    
    print("\n" + "="*80)
    print("Collection completed successfully!")
    print("="*80 + "\n")
    
    # Close logging
    stdout_tee.close()


# ============================================================================
# CONFIGURATION
# ============================================================================

# Choose collection mode: "query" or "dois"
COLLECTION_MODE = "query"  # Change to "dois" to use DOI list

# ============================================================================
# MODE 1: QUERY-BASED COLLECTION
# ============================================================================

# PubMed search query
query = """(("aging"[tiab] OR "ageing"[tiab] OR "senescence"[tiab] OR "longevity"[tiab]) AND
  ("Hallmark*"[ti])
NOT (cosmetic*[tiab] OR sunscreen*[tiab] OR "facial"[tiab] OR dermatol*[tiab])
  NOT ("healthy aging"[tiab] OR wellbeing[tiab] OR "public health"[tiab])
  NOT ("religion"[tiab])
  NOT ("Cosmetics"[mh])
 NOT ("Skin"[mh] OR "Dermatology"[mh])
NOT
("cancer"[TI] OR "ovarian"[TI] OR "liver"[TI] OR "kidne*"[TI] OR "skin"[TI] OR "religion"[TI] OR "enjoyment"[TI]
)
)"""

QUERY_RUN_NAME = "hallmarks_of_aging"  # Descriptive name for query-based run
QUERY_DESCRIPTION = "Hallmarks of aging papers"

# ============================================================================
# MODE 2: DOI-BASED COLLECTION
# ============================================================================

# Option A: Hardcoded DOI list
dois_list = [
    # Add your DOIs here:
    # "10.1038/nature12345",
    # "10.1016/j.cell.2023.01.001",
]

# Option B: Load DOIs from file
DOI_FILE = "data/dois_f.txt"  # Path to file with one DOI per line

DOI_RUN_NAME = "custom_dois"  # Descriptive name for DOI-based run
DOI_DESCRIPTION = "Papers from DOI list"

# ============================================================================
# RUN COLLECTION
# ============================================================================

if __name__ == "__main__":
    try:
        if COLLECTION_MODE == "query":
            # ========================================
            # QUERY-BASED COLLECTION
            # ========================================
            print("Starting paper collection from QUERY...")
            print(f"Expected results: ~46,351 papers")
            collect_papers_to_json(
                query=query, 
                max_results=50000,
                use_threading=True,
                query_description=QUERY_DESCRIPTION,
                run_name=QUERY_RUN_NAME
            )
            
        elif COLLECTION_MODE == "dois":
            # ========================================
            # DOI-BASED COLLECTION
            # ========================================
            print("Starting paper collection from DOIs...")
            
            # Load DOIs from file if specified
            if DOI_FILE and os.path.exists(DOI_FILE):
                print(f"Loading DOIs from: {DOI_FILE}")
                with open(DOI_FILE, 'r') as f:
                    dois_from_file = [line.strip() for line in f if line.strip()]
                print(f"Loaded {len(dois_from_file)} DOIs from file")
                
                collect_papers_from_dois_to_json(
                    dois=dois_from_file,
                    use_threading=True,
                    query_description=DOI_DESCRIPTION,
                    run_name=DOI_RUN_NAME
                )
            elif dois_list:
                # Use hardcoded DOI list
                print(f"Using hardcoded DOI list ({len(dois_list)} DOIs)")
                collect_papers_from_dois_to_json(
                    dois=dois_list,
                    use_threading=True,
                    query_description=DOI_DESCRIPTION,
                    run_name=DOI_RUN_NAME
                )
            else:
                print("ERROR: No DOIs provided!")
                print("Either:")
                print("  1. Set DOI_FILE to a valid file path, or")
                print("  2. Add DOIs to dois_list in the script")
                sys.exit(1)
        else:
            print(f"ERROR: Invalid COLLECTION_MODE '{COLLECTION_MODE}'")
            print("Set COLLECTION_MODE to either 'query' or 'dois'")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user. Exiting...")
    except Exception as e:
        print(f"\n\nError in main execution: {str(e)}")
        import traceback
        traceback.print_exc()
