#!/usr/bin/env python3
"""
Full collection script for broad aging theories and frameworks
Expected results: 46,351 papers
"""
import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import collect_papers

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

# Create logs directory if needed
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                       'paper_collection', 'logs')
os.makedirs(log_dir, exist_ok=True)

# Create log file with timestamp
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = os.path.join(log_dir, f'collection_run_{timestamp}.log')

# Redirect stdout and stderr to both console and file
stdout_tee = TeeOutput(log_file, sys.stdout)
sys.stdout = stdout_tee

# Also capture stderr
stderr_log = os.path.join(log_dir, f'collection_errors_{timestamp}.log')
stderr_tee = TeeOutput(stderr_log, sys.__stderr__)
sys.stderr = stderr_tee

print(f"Logging to: {log_file}")
print(f"Error log: {stderr_log}")
print("="*80)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Broad aging query - verified to return exactly 46,351 results
# queries =["""((“aging"[ti] OR "ageing"[ti] OR "senescence"[ti] OR "longevity"[ti]) AND
#   ( model[ti])
# NOT (cosmetic*[tiab] OR sunscreen*[tiab] OR "facial"[tiab] OR dermatol*[tiab])
#   NOT ("healthy aging"[tiab] OR wellbeing[tiab] OR "public health"[tiab])
#   NOT ("religion"[tiab])
#   NOT ("Cosmetics"[mh])
#  NOT ("Skin"[mh] OR "Dermatology"[mh])
# )"""]

# QUERIES_SUFFIX = """ AND (theory[tiab] OR theories[tiab] OR hypothes*[tiab] OR framework*[tiab] OR paradigm*[tiab] OR "ultimate cause"[tiab] OR "proximate cause"[tiab] OR "evolution*"[tiab])
# AND ( "aging"[Mesh] OR aging[tiab] AND “Aging"[Majr] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])
# NOT (cosmetic*[tiab] OR sunscreen*[tiab] OR "facial"[tiab] OR dermatol*[tiab])
#   NOT ( wellbeing[tiab] OR "public health"[tiab])
#   NOT ("religion"[tiab])
#   NOT ("Cosmetics"[mh])
#  NOT ("Skin"[mh] OR "Dermatology"[mh])
# NOT ("cancer"[TI] OR "ovarian"[TI] OR "liver"[TI] OR "kidne*"[TI] OR "skin"[TI] OR "religion"[TI] OR "enjoyment"[TI])"""

# QUERY_RUN_NAMES = ["aging_text_model"]  # Descriptive name for query-based run

# queries =  [
#     '("mutation accumulation" OR "selection shadow" OR "late-acting" OR medawar[au]) AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("antagonistic pleiotropy") AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("disposable soma" AND "somatic maintenance"[tiab] OR kirkwood[au]) AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '(phenoptosis OR "programmed death" OR "group selection" OR "kin selection") AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("soma"[tiab] OR "evolvable soma") AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("pathogen control") AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("spandrel"[tiab]) AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("intergenerational transfer*" OR "inclusive fitness") AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("danaid"[tiab]) AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("free radical theory") AND (theory[tiab] OR theories[tiab] OR hypothes*[tiab] OR framework*[tiab] OR paradigm*[tiab] OR "ultimate cause"[tiab] OR "proximate cause"[tiab] OR "evolution*"[tiab]) AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("somatic dna damage"[tiab] OR "somatic mutation"[tiab] OR "genomic instability"[tiab]) AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("cross-linking theory") AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("error catastrophe theory") AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("Protein Damage") AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("mitochondrial theory of aging") AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("waste accumulation") AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("Telomere Theory") AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("codon restriction theory") AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("immunological theory" OR "immunosenescence" OR "inflammaging") AND (theory OR theories OR hypothese* OR hypothesi*) AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("hyperfunction theory") AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("developmental theory") AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("stem cell exhaustion"[tiab] OR "stem cell decline"[tiab]) AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("dysdifferentiation") AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("information theory") AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("epigenetic drift" OR "epigenetic damage") AND (theory OR theories OR hypothese* OR hypothesi*) AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("epigenetic clock") AND (theory OR theories OR hypothese* OR hypothesi*) AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '(morphostasis[tiab] OR "morphostatic"[tiab]) AND (theory OR theories OR hypothese* OR hypothesi*) AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '"rate of living" AND (theory OR theories OR hypothese* OR hypothesi*) AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("energy consumption") AND (theory OR theories OR hypothese* OR hypothesi*) AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
# '("energy consumption") AND (theory OR theories OR hypothese* OR hypothesi* )  AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("thermodynamic theory" OR "dissipation theory") AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("hallmarks of aging"[tiab]) AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("disengagement theory") AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("continuity theory"[tiab]) AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("modernization theory"[tiab]) AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("age stratification theory"[tiab]) AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])',
#     '("subculture theory"[tiab]) AND (aging[tiab] OR ageing[tiab] OR Aging[MeSH] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])'
# ]
queries =['("Aging/physiology"[MAJR]) and ("ageing"[tiab] or "aging"[tiab])']




QUERIES_SUFFIX = """ AND (theory[tiab] OR theories[tiab] OR hypothes*[tiab] OR framework*[tiab] OR paradigm*[tiab] OR "ultimate cause"[tiab] OR "proximate cause"[tiab] OR "evolution*"[tiab])
AND ( "aging"[Mesh] OR aging[tiab] AND “Aging"[Majr] OR Geriatrics[MeSH] OR "Cellular Senescence"[Majr] OR "Aging/physiology"[Majr])
NOT (cosmetic*[tiab] OR sunscreen*[tiab] OR "facial"[tiab] OR dermatol*[tiab])
  NOT ( wellbeing[tiab] OR "public health"[tiab])
  NOT ("religion"[tiab])
  NOT ("Cosmetics"[mh])
 NOT ("Skin"[mh] OR "Dermatology"[mh])
NOT ("cancer"[TI] OR "ovarian"[TI] OR "liver"[TI] OR "kidne*"[TI] OR "skin"[TI] OR "religion"[TI] OR "enjoyment"[TI])"""

QUERY_RUN_NAME = 'mesh_aging' # Descriptive name for query-based run

USE_SUFFIX=False
OUTPUT_DIR = None  # Set to custom path or leave as None for default
CHECK_NUM = 60000
# ============================================================================
# RUN COLLECTION
# ============================================================================

try:
    for query in queries:
        query_run_name = QUERY_RUN_NAME
        # Collect papers
        print("Starting paper collection...")
        collect_papers(
            query=query+QUERIES_SUFFIX if USE_SUFFIX else query, 
            max_results=60000,  # Set high enough to capture all 46,351 results
            use_threading=True,  # Enable parallel processing for much faster execution
            output_dir=OUTPUT_DIR,
            query_description=query_run_name,
            check_num=CHECK_NUM
        )

        # Print results location
        base_dir = OUTPUT_DIR if OUTPUT_DIR and os.path.isabs(OUTPUT_DIR) else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), OUTPUT_DIR or 'paper_collection')
        print("\n" + "="*60)
        print("Collection completed! Check the results:")
        print(f"  - Database: {base_dir}/data/papers.db")
        print(f"  - JSON export: {base_dir}/data/papers_export.json")
        print("="*60)

finally:
    # Print log file location
    print("\n" + "="*80)
    print("LOGS SAVED")
    print("="*80)
    print(f"Full log: {log_file}")
    print(f"Error log: {stderr_log}")
    print("="*80)
    
    # Close log files
    stdout_tee.close()
    stderr_tee.close()
