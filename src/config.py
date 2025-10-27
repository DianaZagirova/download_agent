#!/usr/bin/env python3
"""
Configuration file for PubMed paper collection system
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# NCBI/PubMed Configuration - Multiple credentials for load distribution
# Load credentials from environment variables (ENTREZ_EMAIL_1, ENTREZ_API_KEY_1, etc.)
def _load_credentials():
    """Load all available credential pairs from environment variables"""
    credentials = []
    i = 1
    while True:
        email = os.getenv(f"ENTREZ_EMAIL_{i}")
        api_key = os.getenv(f"ENTREZ_API_KEY_{i}")
        
        if not email or not api_key:
            break
            
        credentials.append({
            "email": email,
            "api_key": api_key
        })
        i += 1
    
    # Fallback to single credential if numbered ones don't exist
    if not credentials:
        email = os.getenv("ENTREZ_EMAIL", "sample_email@sample.com")
        api_key = os.getenv("ENTREZ_API_KEY", "sample_api_key")
        credentials.append({"email": email, "api_key": api_key})
    
    return credentials

NCBI_CREDENTIALS = _load_credentials()
print(f"Loaded {len(NCBI_CREDENTIALS)} NCBI credential pair(s)")

# Current credential index (rotates between accounts)
_current_credential_index = 0

def get_current_credentials():
    """Get current NCBI credentials"""
    return NCBI_CREDENTIALS[_current_credential_index]

def rotate_credentials():
    """Switch to next set of credentials"""
    global _current_credential_index
    _current_credential_index = (_current_credential_index + 1) % len(NCBI_CREDENTIALS)
    creds = NCBI_CREDENTIALS[_current_credential_index]
    print(f"Rotated to credentials: {creds['email']}")
    return creds

# Default credentials (first in list)
ENTREZ_EMAIL = NCBI_CREDENTIALS[0]["email"]
ENTREZ_API_KEY = NCBI_CREDENTIALS[0]["api_key"]

# Rate limiting
MAX_REQUESTS_PER_SEC = 8  # NCBI allows 10/sec with API key, we use 8 to be very safe

# OpenAlex Configuration
# OpenAlex rate limits: 10 req/sec, 100k req/day (polite pool gives more consistent response times)
# See: https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication
OPENALEX_EMAIL = NCBI_CREDENTIALS[0]["email"]  # Email for "polite pool" access
OPENALEX_DELAY = 0.15  # 150ms = ~6.7 req/sec per worker (conservative to stay under 10 req/sec total)
OPENALEX_MAX_REQUESTS_PER_DAY = 95000  # Set below 100k limit to have safety margin

# Threading configuration
NUM_THREADS = 2  # Very conservative to prioritize completeness over speed (was 3)
BATCH_SIZE = 30  # Smaller batch size for better rate limiting (was 50)
CHECKPOINT_EVERY = 10  # Save progress every N batches

# Batch fetching configuration
METADATA_FETCH_BATCH_SIZE = 200  # Fetch up to 200 PMIDs per API call (NCBI allows up to 500)
FULLTEXT_PARALLEL_WORKERS = 2  # Conservative parallel workers to respect rate limits

# OpenAlex parallel workers
# IMPORTANT: Reduced from 3 to 1 to avoid hitting 10 req/sec limit
# With OPENALEX_DELAY=0.15s: 1 worker = ~6.7 req/sec (safe), 2 workers = ~13.3 req/sec (exceeds limit)
OPENALEX_PARALLEL_WORKERS = 1  # MUST be 1 to avoid 429 rate limit errors

# OpenAlex batch enrichment
# Use batch API calls to fetch up to 50 DOIs per request (50x faster!)
# Recommended: True (much more efficient and stays under rate limits)
USE_OPENALEX_BATCH_ENRICHMENT = True
OPENALEX_BATCH_SIZE = 50  # Max DOIs per API call (OpenAlex recommends 50)

# Export configuration
# For large databases (>10k papers), JSON export can be slow
SKIP_EXPORT_IF_NO_NEW_PAPERS = True  # Skip export if all papers were skipped (already in DB)
EXPORT_COMPACT_JSON = True  # Use compact JSON (no indentation, 50-70% smaller and faster)
EXPORT_ON_EVERY_RUN = False  # If False, only export when new papers are added

# Directory structure (defaults)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BASE_DIR = os.path.join(PROJECT_ROOT, 'paper_collection')
DEFAULT_DATA_DIR = os.path.join(DEFAULT_BASE_DIR, 'data')

# Current directories (can be overridden)
BASE_DIR = DEFAULT_BASE_DIR
DATA_DIR = DEFAULT_DATA_DIR
CHECKPOINT_DIR = os.path.join(BASE_DIR, 'checkpoints')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
FAILED_DOIS_FILE = os.path.join(BASE_DIR, 'failed_dois.txt')
DATABASE_PATH = os.path.join(DATA_DIR, 'papers.db')

# Create default directories
for directory in [BASE_DIR, DATA_DIR, CHECKPOINT_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)


def set_output_directory(custom_dir: str):
    """
    Set a custom output directory for the collection.
    
    Args:
        custom_dir: Path to custom directory (relative or absolute)
                   If relative, will be relative to PROJECT_ROOT
    
    Returns:
        Dictionary with all configured paths
    """
    global BASE_DIR, DATA_DIR, CHECKPOINT_DIR, LOGS_DIR, FAILED_DOIS_FILE, DATABASE_PATH
    
    # Convert to absolute path if relative
    if not os.path.isabs(custom_dir):
        custom_dir = os.path.join(PROJECT_ROOT, custom_dir)
    
    # Set up directory structure
    BASE_DIR = custom_dir
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    CHECKPOINT_DIR = os.path.join(BASE_DIR, 'checkpoints')
    LOGS_DIR = os.path.join(BASE_DIR, 'logs')
    FAILED_DOIS_FILE = os.path.join(BASE_DIR, 'failed_dois.txt')
    DATABASE_PATH = os.path.join(DATA_DIR, 'papers.db')
    
    # Create directories
    for directory in [BASE_DIR, DATA_DIR, CHECKPOINT_DIR, LOGS_DIR]:
        os.makedirs(directory, exist_ok=True)
    
    return {
        'base_dir': BASE_DIR,
        'data_dir': DATA_DIR,
        'checkpoint_dir': CHECKPOINT_DIR,
        'logs_dir': LOGS_DIR,
        'database_path': DATABASE_PATH
    }

# Retry configuration
MAX_RETRIES = 5  # Increased from 3 to handle transient errors
RETRY_DELAY = 3  # Increased from 2 seconds for better backoff

# Text cleaning configuration
CLEAN_FULL_TEXT = True  # Clean LaTeX and special characters from full text
REMOVE_REFERENCES = True  # Remove references section from full text
CLEAN_ABSTRACT = True  # Clean abstract text
