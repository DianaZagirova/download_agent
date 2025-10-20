# Individual Collection Runs

This directory stores paper collections as JSON files (without database storage).

## Directory Structure

Each collection run creates a timestamped subdirectory:

```
individual_runs/
├── hallmarks_of_aging_20251014_073000/
│   ├── papers_all.json              # All collected papers
│   ├── papers_with_fulltext.json    # Papers with PMC full text
│   ├── papers_without_fulltext.json # Papers without full text
│   ├── statistics.json              # Collection statistics
│   ├── query_info.json             # Query details
│   ├── pmid_list.json              # List of all PMIDs found
│   ├── collection.log              # Full log output
│   └── papers_checkpoint_*.json    # Intermediate checkpoints
└── README.md
```

## Usage

Run the collection script:

```bash
python scripts/run_to_json.py
```

The script will:
1. Search PubMed with the configured query
2. Extract metadata and full text for each paper
3. Enrich with OpenAlex data
4. Save everything to JSON files (no database)
5. Create checkpoints during processing

## Configuration

Edit `scripts/run_to_json.py` to customize:

- `query`: PubMed search query
- `RUN_NAME`: Descriptive name for the collection
- `max_results`: Maximum papers to collect

## Output Files

### papers_all.json
Complete dataset with all papers in JSON format:
```json
[
  {
    "pmid": "12345678",
    "doi": "10.1234/example",
    "title": "Paper title",
    "abstract": "Abstract text...",
    "full_text": "Full text content...",
    "authors": ["Author 1", "Author 2"],
    "year": "2023",
    "journal": "Journal Name",
    "is_full_text_pmc": true,
    ...
  }
]
```

### statistics.json
Collection statistics and metadata:
```json
{
  "query": "...",
  "total_found": 46351,
  "total_processed": 46351,
  "with_full_text": 8234,
  "without_full_text": 38117,
  "with_openalex": 42000,
  "elapsed_minutes": 45.3
}
```

## Advantages vs Database Approach

- **Portable**: JSON files can be easily shared and moved
- **Version Control**: Each run is self-contained
- **No Database Setup**: No SQLite dependencies
- **Easy Data Analysis**: JSON is easily parsed by any tool
- **Backup Friendly**: Each run is a complete backup

## Disadvantages

- **Duplicates**: No automatic deduplication across runs
- **No Querying**: Can't query data efficiently like with SQL
- **Larger Files**: JSON is less storage-efficient than SQLite
- **No Incremental Updates**: Can't easily update existing papers

## Combining Multiple Runs

To merge multiple JSON files:

```python
import json
from pathlib import Path

all_papers = []
for run_dir in Path('individual_runs').iterdir():
    if run_dir.is_dir():
        papers_file = run_dir / 'papers_all.json'
        if papers_file.exists():
            with open(papers_file) as f:
                all_papers.extend(json.load(f))

# Remove duplicates by PMID
seen_pmids = set()
unique_papers = []
for paper in all_papers:
    if paper['pmid'] not in seen_pmids:
        seen_pmids.add(paper['pmid'])
        unique_papers.append(paper)

# Save merged result
with open('merged_papers.json', 'w') as f:
    json.dump(unique_papers, f, indent=2)
```
