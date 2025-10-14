#!/usr/bin/env python3
"""
Configuration file for PubMed paper collection system
"""
import os

# NCBI/PubMed Configuration - Multiple credentials for load distribution
NCBI_CREDENTIALS = [
    {
        "email": "diana.z@insilicomedicine.com",
        "api_key": "9f5d0d5238d7eb65e0526c84d79a5b945d08"
    },
    {
        "email": "kudrjavcev.aleks.2011@post.bio.msu.ru",
        "api_key": "d8cd10c6d3c7feba50589cfda225cebcf309"
    }
]

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
OPENALEX_DELAY = 0.3  # Increased to 300ms to avoid 429 errors (was 0.1)

# Threading configuration
NUM_THREADS = 2  # Very conservative to prioritize completeness over speed (was 3)
BATCH_SIZE = 30  # Smaller batch size for better rate limiting (was 50)
CHECKPOINT_EVERY = 10  # Save progress every N batches

# Batch fetching configuration
METADATA_FETCH_BATCH_SIZE = 200  # Fetch up to 200 PMIDs per API call (NCBI allows up to 500)
FULLTEXT_PARALLEL_WORKERS = 2  # Conservative parallel workers to respect rate limits

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
