#!/usr/bin/env python3
"""
Small test example - collects just 10 papers for testing
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import collect_papers

# ============================================================================
# CONFIGURATION
# ============================================================================

# Simple query that will return results quickly
query = """
(
aging[Title] OR ageing[Title])
 AND ( theory[Title] OR theories[Title] OR hypothesis[Title] OR hypotheses[Title] OR paradigm[Title] OR paradigms[Title])
)
NOT
(Case Reports[Publication Type] OR "case report"[Title] OR "case reports"[Title] OR Clinical Trial[Publication Type] OR "protocol"[Title] OR "conference"[Title] OR "meeting"[Title] OR "well-being"[TI] OR "successful aging"[TI] OR "successful ageing"[TI] OR "ovarian"[TI] OR "liver"[TI] OR "kidne*"[TI] OR "skin"[TI] OR "religion"[TI] OR "enjoyment"[TI] OR "disease hypothesis"[TI] OR "healthy aging"[TI] OR "healthy ageing"[TI] OR "menopause"[TI] 
)
"""

# Custom output directory (optional)
# Default: None (uses 'paper_collection/data')
# Examples:
#   - Relative path: 'aging_theories_collection'
#   - Absolute path: '/Users/diana/Documents/my_papers'
OUTPUT_DIR = None  # Set to custom path or leave as None for default

# ============================================================================
# RUN COLLECTION
# ============================================================================

# Collect papers
print("Starting paper collection...")
collect_papers(
    query=query, 
    max_results=4000, 
    use_threading=True,  # Enable parallel processing for much faster execution
    output_dir=OUTPUT_DIR
)

# Print results location
if OUTPUT_DIR:
    base_dir = OUTPUT_DIR if os.path.isabs(OUTPUT_DIR) else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), OUTPUT_DIR)
    print("\n" + "="*60)
    print("Collection completed! Check the results:")
    print(f"  - Database: {base_dir}/data/papers.db")
    print(f"  - JSON export: {base_dir}/data/papers_export.json")
    print("="*60)
else:
    print("\n" + "="*60)
    print("Collection completed! Check the results:")
    print("  - Database: ./paper_collection/data/papers.db")
    print("  - JSON export: ./paper_collection/data/papers_export.json")
    print("="*60)
