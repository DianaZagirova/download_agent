"""
PubMed Paper Collection System - Core Package
"""
from .config import *
from .models import PaperMetadata, CollectionStats
from .database import PaperDatabase
from .pubmed_extractor import search_pubmed, process_paper, extract_pmc_fulltext
from .openalex_extractor import enrich_with_openalex
from .text_cleaner import clean_text_comprehensive, clean_abstract

__version__ = "1.0.0"
__all__ = [
    'PaperMetadata',
    'CollectionStats',
    'PaperDatabase',
    'search_pubmed',
    'process_paper',
    'extract_pmc_fulltext',
    'enrich_with_openalex',
    'clean_text_comprehensive',
    'clean_abstract',
]
