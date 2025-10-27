#!/usr/bin/env python3
"""
Full collection script for broad aging theories and frameworks
Expected results: 46,351 papers

Usage:
    python run_full.py --queries "query1" "query2" --queries-suffix "suffix" --query-run-name "run_name"
    python run_full.py --queries "(\"Aging/physiology\"[MAJR]) and (\"ageing\"[tiab] or \"aging\"[tiab])" --queries-suffix "AND (theory[tiab] OR theories[tiab])" --query-run-name "mesh_aging"
    python run_full.py --config config/theory_aging_2024.json
"""
import sys
import os
import argparse
import json
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
# ARGUMENT PARSING
# ============================================================================

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Full collection script for broad aging theories and frameworks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using command line arguments:
  python run_full.py --queries "(\"Aging/physiology\"[MAJR]) and (\"ageing\"[tiab] or \"aging\"[tiab])" --queries-suffix "AND (theory[tiab] OR theories[tiab])" --query-run-name "mesh_aging"
  
  python run_full.py --queries "query1" "query2" --queries-suffix "suffix" --query-run-name "custom_run"
  
  # Using config file:
  python run_full.py --config config/theory_aging_2024.json
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to JSON config file with all parameters'
    )
    
    parser.add_argument(
        '--queries',
        nargs='+',
        help='One or more search queries to execute'
    )
    
    parser.add_argument(
        '--queries-suffix',
        type=str,
        default='',
        help='Suffix to append to all queries (optional)'
    )
    
    parser.add_argument(
        '--query-run-name',
        type=str,
        help='Descriptive name for the query-based run'
    )
    
    parser.add_argument(
        '--use-suffix',
        action='store_true',
        help='Whether to append the queries suffix to queries'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Custom output directory (optional)'
    )
    
    parser.add_argument(
        '--max-results',
        type=int,
        default=60000,
        help='Maximum number of results to collect (default: 60000)'
    )
    
    parser.add_argument(
        '--check-num',
        type=int,
        default=60000,
        help='Number to check against for validation (default: 60000)'
    )
    
    parser.add_argument(
        '--test-db',
        action='store_true',
        help='Use test database instead of main database (saves to test_papers.db)'
    )
    
    return parser.parse_args()

# Parse command line arguments
args = parse_arguments()

# ============================================================================
# CONFIGURATION
# ============================================================================

# Load from config file if provided
if args.config:
    config_path = args.config
    if not os.path.isabs(config_path):
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config_path)
    
    print(f"Loading configuration from: {config_path}")
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Load all parameters from config
    queries = config.get('queries', [])
    QUERIES_SUFFIX = config.get('queries_suffix', '')
    QUERY_RUN_NAME = config.get('query_run_name', 'unnamed_run')
    USE_SUFFIX = config.get('use_suffix', False)
    CHECK_NUM = config.get('check_num', 60000)
    MAX_RESULTS = config.get('max_results', 60000)
    USE_TEST_DB = config.get('test_db', False)
    OUTPUT_DIR = config.get('output_dir', None)
    
    print(f"Loaded config: {json.dumps(config, indent=2)}")
else:
    # Use parsed arguments from command line
    if not args.queries or not args.query_run_name:
        print("ERROR: --queries and --query-run-name are required when not using --config")
        sys.exit(1)
    
    queries = args.queries
    QUERIES_SUFFIX = args.queries_suffix
    QUERY_RUN_NAME = args.query_run_name
    USE_SUFFIX = args.use_suffix
    CHECK_NUM = args.check_num
    MAX_RESULTS = args.max_results
    USE_TEST_DB = args.test_db
    OUTPUT_DIR = args.output_dir

# Handle output directory - use test database if requested
if USE_TEST_DB:
    # Create test-specific output directory
    base_output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'paper_collection_test')
    if not OUTPUT_DIR:
        OUTPUT_DIR = base_output_dir
    print(f"Using TEST DATABASE: {OUTPUT_DIR}")

# Print configuration
print("Configuration:")
print(f"  Queries: {queries}")
print(f"  Queries Suffix: {QUERIES_SUFFIX}")
print(f"  Query Run Name: {QUERY_RUN_NAME}")
print(f"  Use Suffix: {USE_SUFFIX}")
print(f"  Output Dir: {OUTPUT_DIR or 'default'}")
print(f"  Max Results: {MAX_RESULTS}")
print(f"  Check Num: {CHECK_NUM}")
print(f"  Test Database: {USE_TEST_DB}")
print("="*80)
# ============================================================================
# RUN COLLECTION
# ============================================================================

try:
    for query in queries:
        query_run_name = QUERY_RUN_NAME
        
        # Collect papers
        print("Starting paper collection...")
        
        # Handle test database by monkey-patching the config after collect_papers sets it
        if USE_TEST_DB and OUTPUT_DIR:
            # Store original collect_papers function
            from main import collect_papers as original_collect_papers
            from src.config import set_output_directory
            import src.config
            
            def patched_collect_papers(*args, **kwargs):
                # Call the original function but patch DATABASE_PATH after set_output_directory
                # We need to patch it right after the output directory is set
                original_set_output_directory = set_output_directory
                
                def patched_set_output_directory(custom_dir):
                    result = original_set_output_directory(custom_dir)
                    # Override the database path to use test database
                    src.config.DATABASE_PATH = os.path.join(result['data_dir'], 'test_papers.db')
                    print(f"Test database path set to: {src.config.DATABASE_PATH}")
                    return result
                
                # Temporarily replace the function
                import src.config
                src.config.set_output_directory = patched_set_output_directory
                
                try:
                    return original_collect_papers(*args, **kwargs)
                finally:
                    # Restore original function
                    src.config.set_output_directory = original_set_output_directory
            
            # Use the patched version
            collect_papers_func = patched_collect_papers
        else:
            collect_papers_func = collect_papers
        
        collect_papers_func(
            query=query+QUERIES_SUFFIX if USE_SUFFIX else query, 
            max_results=MAX_RESULTS,  # Use configurable max results
            use_threading=True,  # Enable parallel processing for much faster execution
            output_dir=OUTPUT_DIR,
            query_description=query_run_name,
            check_num=CHECK_NUM
        )

        # Print results location
        base_dir = OUTPUT_DIR if OUTPUT_DIR and os.path.isabs(OUTPUT_DIR) else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), OUTPUT_DIR or 'paper_collection')
        db_name = "test_papers.db" if USE_TEST_DB else "papers.db"
        json_name = "test_papers_export.json" if USE_TEST_DB else "papers_export.json"
        
        print("\n" + "="*60)
        print("Collection completed! Check the results:")
        print(f"  - Database: {base_dir}/data/{db_name}")
        print(f"  - JSON export: {base_dir}/data/{json_name}")
        if USE_TEST_DB:
            print("  - NOTE: Using TEST DATABASE - data saved separately from main collection")
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
