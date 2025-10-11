# PubMed Paper Collection System

A comprehensive, scalable system for collecting scientific papers from PubMed with metadata extraction from both PubMed and OpenAlex.

## Features

- **PubMed Integration**: Search and retrieve papers using E-utilities
- **Full-Text Extraction**: Automatically extracts full text from PubMed Central (PMC) when available
- **Text Cleaning**: Removes LaTeX commands, special characters, and formatting artifacts
- **OpenAlex Enrichment**: Enhances metadata with citation metrics and open access information
- **Structured Storage**: SQLite database with JSON export capabilities
- **Multi-threaded Processing**: Efficient parallel processing with rate limiting
- **Checkpoint System**: Automatic progress saving for large collections
- **Comprehensive Metadata**: Extracts 20+ fields per paper

## Extracted Metadata

### From PubMed:
- `pmid` - PubMed ID
- `pmcid` - PubMed Central ID (if available)
- `doi` - Digital Object Identifier
- `title` - Paper title
- `abstract` - Abstract text
- `full_text` - Full text content (without abstract)
- `mesh_terms` - Medical Subject Headings
- `keywords` - Author keywords
- `authors` - List of authors
- `year` - Publication year
- `date_published` - Full publication date
- `journal` - Journal name
- `is_full_text_pmc` - Whether full text is available in PMC

### From OpenAlex:
- `oa_url` - Open access URL
- `primary_topic` - Primary research topic
- `citation_normalized_percentile` - Citation percentile
- `cited_by_count` - Number of citations
- `fwci` - Field-Weighted Citation Impact

### System Fields:
- `collection_date` - When the paper was collected
- `openalex_retrieved` - Whether OpenAlex data was successfully retrieved

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your credentials in `config.py`:
   - Set your email for NCBI E-utilities
   - Add your NCBI API key (get one at https://www.ncbi.nlm.nih.gov/account/)

## Usage

### Basic Usage

Run the main script with the default query:
```bash
python main.py
```

### Custom Query

Edit `main.py` and modify the `query` variable in the `main()` function:

```python
query = """
(
  (
    aging[Title] OR ageing[Title] 
  )
  AND
  (
    theory[Title] OR theories[Title] OR hypothesis[Title]
  )
)
NOT
(
  Case Reports[Publication Type] OR "case report"[Title]
)
"""
```

### Programmatic Usage

```python
from main import collect_papers

# Define your PubMed query
query = "your PubMed query here"

# Collect papers
collect_papers(query, max_results=10000, use_threading=True)
```

### Working with the Database

```python
from database import PaperDatabase

# Open database
db = PaperDatabase()

# Get all papers
papers = db.get_all_papers()

# Get papers with full text
papers_with_fulltext = db.get_papers_with_fulltext()

# Get papers without full text
papers_without_fulltext = db.get_papers_without_fulltext()

# Get a specific paper
paper = db.get_paper("12345678")  # PMID

# Export to JSON
db.export_to_json("my_papers.json")

# Export failed DOIs
db.export_failed_dois_to_file("failed_dois.txt")

# Get statistics
stats = db.get_statistics()
print(stats)

db.close()
```

## Project Structure

```
get_paper_by_query/
├── main.py                          # Main entry point
├── download_papers_full_texts.py   # Alternative download script
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
├── PROJECT_STRUCTURE.md            # Detailed structure documentation
│
├── src/                            # Core package
│   ├── config.py                   # Configuration
│   ├── models.py                   # Data models
│   ├── database.py                 # Database handler
│   ├── pubmed_extractor.py         # PubMed integration
│   ├── openalex_extractor.py       # OpenAlex integration
│   └── text_cleaner.py             # Text cleaning
│
├── scripts/                        # Utility scripts
│   ├── test_small.py               # Quick test
│   ├── example_usage.py            # Usage examples
│   ├── reclean_database.py         # Re-clean papers
│   └── test_cleaner_integration.py # Test cleaning
│
├── docs/                           # Documentation
│   ├── SYSTEM_OVERVIEW.md          # Technical details
│   └── TEXT_CLEANING_GUIDE.md      # Cleaning guide
│
└── paper_collection/               # Output (auto-created)
    ├── data/
    │   ├── papers.db               # SQLite database
    │   ├── papers_export.json      # JSON export
    │   └── failed_dois.txt         # Papers without full text
    ├── checkpoints/                # Progress saves
    └── logs/                       # Log files
```

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed documentation.

## Configuration

Edit `src/config.py` to customize:

- **API Credentials**: `ENTREZ_EMAIL`, `ENTREZ_API_KEY`
- **Rate Limiting**: `MAX_REQUESTS_PER_SEC`, `OPENALEX_DELAY`
- **Threading**: `NUM_THREADS`, `BATCH_SIZE`
- **Checkpoints**: `CHECKPOINT_EVERY`
- **Directories**: `BASE_DIR`, `DATA_DIR`, etc.

## Output Files

After running the collection:

1. **SQLite Database** (`paper_collection/data/papers.db`): 
   - Structured storage of all papers
   - Queryable with SQL
   - Includes collection statistics

2. **JSON Export** (`paper_collection/data/papers_export.json`):
   - All papers in JSON format
   - Easy to import into other tools
   - Human-readable

3. **Failed DOIs** (`paper_collection/data/failed_dois.json`):
   - Structured JSON of papers without PMC full text
   - Includes DOI, PMID, title, journal, authors, abstract preview, and OA URL
   - Can be used for alternative full-text retrieval
   - Also available in TXT format for backward compatibility

## Example Query

The default query searches for papers about aging theories:

```
(
  (aging[Title] OR ageing[Title])
  AND
  (theory[Title] OR theories[Title] OR hypothesis[Title])
)
NOT
(
  Case Reports[Publication Type] OR "case report"[Title] OR
  "protocol"[Title] OR "conference"[Title]
)
```

## Rate Limiting

The system respects NCBI and OpenAlex rate limits:
- **NCBI**: 9 requests/second (with API key, limit is 10)
- **OpenAlex**: 0.1 second delay between requests

## Error Handling

- Automatic retries (3 attempts) for failed API calls
- Checkpoint system saves progress every 32 batches
- Failed papers are logged and can be reprocessed
- Thread-safe database operations

## Performance

- Multi-threaded processing (default: 2 threads)
- Batch processing (default: 20 papers per batch)
- Typical speed: ~100-200 papers per minute (depends on full-text availability)

## Troubleshooting

### No papers found
- Check your PubMed query syntax
- Verify your NCBI credentials
- Check internet connection

### Slow processing
- Reduce `NUM_THREADS` if hitting rate limits
- Increase `BATCH_SIZE` for better throughput
- Disable OpenAlex enrichment for faster collection

### Database errors
- Ensure write permissions in output directory
- Check disk space
- Close other connections to the database

## Advanced Usage

### Skip OpenAlex Enrichment

Modify `process_paper_with_openalex()` in `main.py` to skip OpenAlex:

```python
def process_paper_with_openalex(pmid: str):
    metadata = process_paper(pmid)
    if metadata is None:
        return None, False, False
    return metadata, True, False  # Skip OpenAlex
```

### Custom Metadata Extraction

Extend the `PaperMetadata` class in `models.py` to add custom fields.

### Export to Other Formats

Use the database API to export to CSV, Excel, or other formats:

```python
import pandas as pd
from database import PaperDatabase

db = PaperDatabase()
papers = db.get_all_papers()
df = pd.DataFrame([p.to_dict() for p in papers])
df.to_csv('papers.csv', index=False)
```

## License

This project is provided as-is for research purposes.

## Support

For issues or questions, please check:
- NCBI E-utilities documentation: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- OpenAlex API documentation: https://docs.openalex.org/
- Biopython documentation: https://biopython.org/wiki/Documentation
