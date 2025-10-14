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
query = """((“aging"[tiab] OR "ageing"[tiab] OR "senescence"[tiab] OR "longevity"[tiab]) AND
  (“Hallmark*”[ti])
NOT (cosmetic*[tiab] OR sunscreen*[tiab] OR "facial"[tiab] OR dermatol*[tiab])
  NOT ("healthy aging"[tiab] OR wellbeing[tiab] OR "public health"[tiab])
  NOT ("religion"[tiab])
  NOT ("Cosmetics"[mh])
 NOT ("Skin"[mh] OR "Dermatology"[mh])
NOT
(“cancer”[TI] OR “ovarian”[TI] OR “liver”[TI] OR “kidne*”[TI] OR “skin”[TI] OR “religion”[TI] OR “enjoyment”[TI]
)
)"""

# Custom output directory (optional)
# Default: None (uses 'paper_collection/data')
# Examples:
#   - Relative path: 'aging_theories_collection'
#   - Absolute path: '/Users/diana/Documents/my_papers'
OUTPUT_DIR = None  # Set to custom path or leave as None for default

# ============================================================================
# RUN COLLECTION
# ============================================================================

try:
    # Collect papers
    print("Starting paper collection...")
    print(f"Expected results: 46,351 papers")
    collect_papers(
        query=query, 
        max_results=50000,  # Set high enough to capture all 46,351 results
        use_threading=True,  # Enable parallel processing for much faster execution
        output_dir=OUTPUT_DIR,
        query_description="hallmarks_of_aging"
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
