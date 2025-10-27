
# 🧬 Aging Theories Literature Collection System

Collect Stage 1 of a multi-phase effort to systematically **discover, download, and classify scientific theories of aging**. This repository focuses on maximizing recall so future stages can curate, annotate, and analyze a truly comprehensive corpus.

## 📌 Overview

- **Stage 1 Goal:** Capture as many aging-theory papers as possible, accepting lower precision in exchange for high recall.
- **Why it matters:** Aging research spans evolutionary biology, biomedicine, systems science, and more. Important theories are scattered across disciplines and rarely share consistent terminology. Without a broad-first approach, foundational work is easy to miss.
- **Guiding principle:** Cast a wide net now, refine later. Subsequent stages will add filtering, classification, and expert review.

### Data Coverage Strategy

1. **Diverse sources** provide broad disciplinary reach:
   - **PubMed:** Biomedical and life sciences literature
   - **arXiv:** Theoretical and computational biology preprints
   - **bioRxiv & medRxiv:** Rapidly evolving preprint ecosystems
   - **OpenAlex:** Citation, field tags, and enrichment metadata
   - **Europe PMC:** Additional full-text biomedical coverage
2. **Diverse queries** surface terminology variants, synonyms, and adjacent concepts to minimize blind spots.

> 📝 **Status:** The current pipeline has already surfaced **108,000+ unique records**, forming a rich base for downstream filtering and analysis.

---

## 🚀 Quick Start

### 1. Clone & Set Up

```bash
git clone <repository-url>
cd download_papers_pubmed

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Optional helper
bash setup.sh

copy .env.example and add variables
```

### 2. Run the Demo

```bash
python demo.py
```

The demo executes three representative queries, returning roughly 150 papers and exporting:
- **SQLite database:** `paper_collection_test/data/test_papers.db`
- **JSON snapshot:** `paper_collection_test/data/test_papers_export.json`
- **Basic stats and logs:** stored under `paper_collection_test/data/`

> 💡 **See example output:** Check `data/example_papers.json` for 2 complete paper records showing all collected fields (metadata, full text, citations, topics, etc.)

### 3. Launch a Custom Crawl

#### Option A: Command Line Arguments

```bash
python scripts/run_full.py \
  --queries "(\"theory of aging\"[Title]) AND (\"Aging\"[Mesh]) AND (2020:2025[dp]) AND (full text[sb])" \
  --query-run-name "recent_aging_theories" \
  --max-results 1000 \
  --test-db
```

#### Option B: JSON Configuration File (Recommended)

For easier management and reproducibility, use a JSON config file:

```bash
python scripts/run_full.py --config config/theory_aging_2024.json
```

**Example config file** (`config/theory_aging_2024.json`):
```json
{
  "queries": [
    "\"theory of aging\"[Title/Abstract] AND 2024[dp]"
  ],
  "queries_suffix": "",
  "query_run_name": "theory_aging_2024",
  "use_suffix": false,
  "max_results": 10000,
  "check_num": 10000,
  "test_db": false,
  "output_dir": null
}
```

**Config file parameters:**
- `queries`: List of PubMed search queries
- `queries_suffix`: Optional suffix to append to all queries
- `query_run_name`: Descriptive name for the run
- `use_suffix`: Whether to append the suffix to queries
- `max_results`: Maximum papers to collect per query
- `check_num`: Expected result count for validation
- `test_db`: Use test database (true) or main database (false)
- `output_dir`: Custom output directory (null = default)

See `config/README.md` for more examples and PubMed query syntax.

Outputs land under `paper_collection/data/` (or `paper_collection_test/data/` with `--test-db`) in both SQLite and JSON formats, making it easy to inspect results or feed them into notebooks.

---

## 🧐 How It Works

### Collection Process Flow

```
Query → PubMed Search → Metadata Extraction → Full Text Retrieval → OpenAlex Enrichment → Database Storage
```

#### Step-by-Step Process

1. **Query Execution**
   - Submit PubMed query via Entrez API
   - Retrieve list of PMIDs (PubMed IDs)
   - Handle pagination for large result sets

2. **Metadata Extraction** (from PubMed)
   - **Basic fields**: PMID, DOI, title, abstract, authors, journal, publication date
   - **MeSH terms**: Medical Subject Headings for topic classification
   - **Keywords**: Author-provided keywords
   - **PMC ID**: If full text is available in PubMed Central

3. **Full Text Retrieval** (when available)
   - Extract from PubMed Central (PMC) using PMC ID
   - Parse structured sections (Introduction, Methods, Results, Discussion, etc.)
   - Clean LaTeX, special characters, and references
   - Store both flat text and sectioned format

4. **OpenAlex Enrichment** (citation & topic data)
   - **Citation metrics**: Citation count, normalized percentile, FWCI (Field-Weighted Citation Impact)
   - **Topic classification**: Primary topic with hierarchical taxonomy (domain → field → subfield → topic)
   - **Open access URL**: Direct link to full text when available

5. **Database Storage**
   - Deduplicate by PMID (primary key)
   - Store in SQLite with full-text search capabilities
   - Export to JSON for portability and analysis

### Data Records Structure

Each paper record contains:

**PubMed Fields:**
- `pmid` (str): PubMed ID - unique identifier
- `pmcid` (str): PubMed Central ID - if full text available
- `doi` (str): Digital Object Identifier
- `title` (str): Paper title
- `abstract` (str): Abstract text (cleaned)
- `full_text` (str): Full text in flat format
- `full_text_sections` (dict): Structured full text by section
- `mesh_terms` (list): MeSH subject headings
- `keywords` (list): Author keywords
- `authors` (list): Author names
- `year` (str): Publication year
- `date_published` (str): Full publication date
- `journal` (str): Journal name
- `is_full_text_pmc` (bool): Whether full text was retrieved

**OpenAlex Fields:**
- `oa_url` (str): Open access URL
- `primary_topic` (dict): Topic classification with hierarchy
- `citation_normalized_percentile` (float): Citation percentile (0-1)
- `cited_by_count` (int): Number of citations
- `fwci` (float): Field-Weighted Citation Impact

**System Fields:**
- `collection_date` (str): When the record was collected
- `openalex_retrieved` (bool): Whether OpenAlex data was successfully retrieved
- `query_id` (int): Reference to the query used
- `source` (str): Data source (PubMed, BioRxiv, etc.)

**Example:** See `data/example_papers.json` for 2 complete paper records showing all fields.

### Data Quality & Coverage

**What gets collected:**
- ✅ **All papers**: Basic metadata (title, abstract, authors, journal, dates)
- ✅ **~40-60%**: Full text from PubMed Central (when available)
- ✅ **~80-90%**: OpenAlex enrichment (citations, topics, open access links)
- ✅ **All papers**: MeSH terms for medical topic classification

**Data completeness by field:**
```
Field                    Coverage    Source
────────────────────────────────────────────
pmid                     100%        PubMed (primary key)
title                    ~99%        PubMed
abstract                 ~95%        PubMed
doi                      ~85%        PubMed
full_text                ~40-60%     PubMed Central
mesh_terms               ~90%        PubMed
authors                  ~98%        PubMed
journal                  ~99%        PubMed
cited_by_count           ~80-90%     OpenAlex
primary_topic            ~80-90%     OpenAlex
oa_url                   ~30-50%     OpenAlex
```

**Quality features:**
- Automatic deduplication by PMID
- Text cleaning (LaTeX, special characters, references)
- Structured section parsing for full text
- Validation of DOIs and dates
- Provenance tracking (query_id, collection_date, source)

### Database Schema

**papers** table (main storage):
```sql
pmid TEXT PRIMARY KEY,
pmcid TEXT,
doi TEXT,
title TEXT,
abstract TEXT,
full_text TEXT,
full_text_sections TEXT (JSON),
mesh_terms TEXT (JSON array),
keywords TEXT (JSON array),
authors TEXT (JSON array),
year TEXT,
date_published TEXT,
journal TEXT,
is_full_text_pmc INTEGER (boolean),
oa_url TEXT,
primary_topic TEXT (JSON),
topic_name TEXT,
topic_subfield TEXT,
topic_field TEXT,
topic_domain TEXT,
citation_normalized_percentile REAL,
cited_by_count INTEGER,
fwci REAL,
collection_date TEXT,
openalex_retrieved INTEGER (boolean),
query_id INTEGER,
source TEXT
```

**queries** table (query tracking):
```sql
id INTEGER PRIMARY KEY,
query_text TEXT,
description TEXT,
created_date TEXT
```

**collection_runs** table (run statistics):
```sql
id INTEGER PRIMARY KEY,
query TEXT,
total_found INTEGER,
total_processed INTEGER,
with_full_text INTEGER,
without_full_text INTEGER,
start_time TEXT,
end_time TEXT,
duration_seconds REAL
```

### Technical Highlights

- **Parallel multi-threaded fetching** keeps throughput high even for large query batches
- **Batch API calls** fetch up to 200 PMIDs per request, 50 DOIs per OpenAlex call
- **API-aware rate limiting** respects NCBI (10 req/sec) and OpenAlex (10 req/sec) limits
- **Multiple credential support** distributes load across multiple NCBI API keys
- **Smart caching** avoids re-fetching existing records
- **Data integrity checks** validate DOIs, track provenance, and deduplicate records
- **Reproducible runs** via pinned dependencies, structured logs, and consistent output formats
- **Progress checkpoints** save state every N batches for resumable collections

---

## 🔍 Query Design Examples

- **Broad coverage:** aging, longevity, senescence, life-history frameworks.
- **Theory spotlights:** mutation accumulation, antagonistic pleiotropy, disposable soma, hallmarks of aging, mitochondrial/free-radical models.
- **Interventions & model organisms:** caloric restriction, pharmacological and genetic interventions, C. elegans, Drosophila, mice, and more.

The complete set of AI-generated queries (40+ theoretical frameworks) lives in `data/queries_used.json`.

---

## 🗂️ Repository Layout

```
download_papers_pubmed/
├── src/                          # Core extraction and processing modules
│   ├── pubmed_extractor.py       # PubMed API integration
│   ├── openalex_extractor.py     # OpenAlex enrichment
│   ├── database.py               # SQLite database operations
│   ├── models.py                 # Data models
│   └── config.py                 # Configuration and credentials
├── scripts/                      # Execution scripts
│   ├── run_full.py               # Main collection script
│   ├── run_from_dois.py          # DOI-based collection
│   └── demo.py                   # Quick demonstration
├── config/                       # JSON configuration files
│   ├── theory_aging_2024.json    # Example: theory of aging in 2024
│   ├── aging_theories_recent.json # Example: recent theories
│   ├── example_template.json     # Template for new configs
│   └── README.md                 # Config documentation
├── data/
│   ├── queries_used.json         # Historical query records
│   └── example_papers.json       # Example output: 2 complete paper records
├── paper_collection/             # Main output directory
│   ├── data/                     # Database and JSON exports
│   ├── logs/                     # Execution logs
│   └── checkpoints/              # Progress checkpoints
├── paper_collection_test/        # Test database output
├── main.py                       # Main orchestrator
├── demo.py                       # Demo script
├── requirements.txt              # Python dependencies
└── .env                          # API credentials (create from .env.example)
```

---

## 📖 Common Use Cases

### Quick Test Run
```bash
# Test with small dataset using config file
python scripts/run_full.py --config config/theory_aging_2024.json
```

### Production Collection
```bash
# Large-scale collection with command line
python scripts/run_full.py \
  --queries "aging[tiab] AND theory[tiab]" \
  --query-run-name "aging_theories_full" \
  --max-results 50000
```

### Multiple Queries with Shared Filter
```bash
# Use config file for complex multi-query setup
python scripts/run_full.py --config config/aging_theories_recent.json
```

### DOI-Based Collection
```bash
# Collect specific papers by DOI
python scripts/run_from_dois.py --dois-file my_dois.txt
```

### Environment Setup
```bash
# Copy and configure credentials
cp .env.example .env
# Edit .env to add your NCBI API credentials
# Supports multiple credential pairs for load distribution
```

---

## 🛣️ CODE FOR THE NEXT STEP 

- **Stage 2:** Full-text retrieval and enrichment – see https://github.com/DianaZagirova/scihub_api

Contributions and issue reports that improve search coverage, data quality, or documentation are warmly welcomed.