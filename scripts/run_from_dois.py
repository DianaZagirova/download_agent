#!/usr/bin/env python3
"""
Collect papers from a list of DOIs
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import collect_papers_from_dois

# ============================================================================
# CONFIGURATION
# ============================================================================

# Option 1: Provide DOIs directly in the script
DOIS = [
   '10.1007/BF02008340',
 '10.1016/0014-4827(61)90192-6',
 '10.1016/0531-5565(87)90010-6',
 '10.1016/j.cell.2011.07.030',
 '10.1016/j.cell.2024.01.013',
 '10.1038/345458a0',
 '10.1073/pnas.0509776102',
 '10.1093/geronj/11.3.298',
 '10.1155/2016/8426874',
 '10.1186/1742-4933-1-1',
 '10.14336/AD.2019.0820',
 '10.18632/aging.100253',
 '10.18632/oncoscience.545',
 '10.20463/jenb.2017.0027',
 '10.3389/fcell.2020.575645',
 '10.3389/fphys.2021.724506',
 '10.3389/fragi.2022.866718'
]
# DOIS = ['10.20463/jenb.2017.0027']
DOI_FILE= ""
# Option 2: Load DOIs from a file (one DOI per line)
# DOI_FILE = "data/dois_validation/dois_validation3.txt"
# DOI_FILE=None
# Custom output directory (optional)
# Default: None (uses 'paper_collection/data')
# Examples:
#   - Relative path: 'doi_collection'
#   - Absolute path: '/Users/diana/Documents/my_papers'
OUTPUT_DIR = None  # Set to custom path or leave as None for default (paper_collection)

# Threading configuration
USE_THREADING = True  # Set to False for debugging

# ============================================================================
# LOAD DOIs
# ============================================================================

def load_dois_from_file(filepath):
    """Load DOIs from a text file (one DOI per line)"""
    dois = []
    with open(filepath, 'r') as f:
        for line in f:
            doi = line.strip()
            if doi and not doi.startswith('#'):  # Skip empty lines and comments
                dois.append(doi)
    return dois


# Load DOIs from file if specified, otherwise use the list
if DOI_FILE:
    print(f"Loading DOIs from file: {DOI_FILE}")
    dois_to_collect = load_dois_from_file(DOI_FILE)
else:
    dois_to_collect = DOIS

print(f"Total DOIs to process: {len(dois_to_collect)}")

if not dois_to_collect:
    print("Error: No DOIs provided!")
    print("Either set DOIS list or DOI_FILE in the script.")
    sys.exit(1)

# ============================================================================
# RUN COLLECTION
# ============================================================================

print("Starting paper collection from DOIs...")
collect_papers_from_dois(
    dois=dois_to_collect,
    use_threading=USE_THREADING,
    output_dir=OUTPUT_DIR,
    query_description=f"DOI collection: {len(dois_to_collect)} papers"
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
