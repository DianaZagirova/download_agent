# Aging Theories Literature Collection System

## Project Overview

This repository implements **Step 1** of a multi-phase project to systematically collect and classify aging theories from scientific literature. The primary goal is to achieve maximum recall in identifying aging-related theoretical papers, prioritizing comprehensive coverage over precision at this initial stage.

### Context and Importance

Aging research encompasses numerous theoretical frameworks spanning evolutionary biology, molecular mechanisms, and systems-level approaches. Traditional literature searches often miss relevant papers due to inconsistent terminology, interdisciplinary nature, and the breadth of aging-related research. This system addresses these challenges through AI-powered query generation and multi-source data integration.

**Why High Recall Matters**: At this stage, we prioritize catching all potentially relevant aging-theory literature, even if it means including some less relevant papers. This comprehensive approach ensures we don't miss important theoretical contributions that might be excluded by overly restrictive search criteria.

## Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd download_papers_pubmed

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

or use setup.sh to set up env

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Demonstration

```bash
# Run the demo script
python demo.py
```

The demo will:
- Execute 3 diverse aging research queries
- Collect 150 papers total (50 per query)
- Save results to `paper_collection_test/data/test_papers.db`
- Export data to `paper_collection_test/data/test_papers_export.json`
- Display collection statistics and performance metrics

### 3. Custom Query Example

```bash
# Run a specific query for recent aging theories
python scripts/run_full.py \
  --queries "(\"theory of aging\"[Title]) AND (\"Aging\"[Mesh]) AND (2020:2025[dp]) AND (full text[sb])" \
  --query-run-name "recent_aging_theories" \
  --max-results 1000 \
  --test-db
```

**Results Location**:
- Database: `paper_collection_test/data/test_papers.db`
- JSON Export: `paper_collection_test/data/test_papers_export.json`
- Logs: `paper_collection_test/logs/`

## How the System Works

### Step 1: AI-Powered Query Generation

The system begins with deep analysis of the aging research landscape to generate comprehensive PubMed search queries. This involves:

- **Theory-Specific Queries**: Individual queries for each major aging theory (mutation accumulation, antagonistic pleiotropy, disposable soma, etc.)
- **Domain Coverage**: Queries spanning evolutionary, molecular, systems, and intervention-based approaches
- **Terminology Analysis**: Systematic exploration of aging-related terminology and synonyms

### Step 2: Iterative Query Refinement

AI feedback mechanisms continuously refine queries for optimal specificity and relevance:

- **Hit Count Monitoring**: Queries are evaluated based on PubMed result counts
- **Relevance Assessment**: Results are analyzed for theoretical content
- **Query Optimization**: Overly broad queries are refined, overly narrow queries are expanded
- **Exclusion Filtering**: Non-relevant domains (cosmetics, dermatology) are systematically excluded

### Step 3: Multi-Source Data Extraction

Automated search and extraction from multiple scholarly databases:

- **PubMed**: Core metadata, abstracts, and MeSH terms
- **OpenAlex**: Citation counts, research fields, and institutional affiliations
- **PMC**: Full-text articles when available
- **Europe PMC**: Alternative full-text sources for comprehensive coverage

### Step 4: Efficient Data Storage

Results are stored in a well-structured, fast-access database:

- **SQLite Database**: Optimized schema for complex queries and relationships
- **JSON Export**: Portable data format for analysis and sharing
- **Metadata Tracking**: Complete provenance and quality metrics
- **Incremental Updates**: Support for ongoing collection and refinement

## Query Strategy

The system employs a multi-layered query approach covering diverse conceptual angles:

### Broad Thematic Queries
- General aging and longevity research
- Senescence mechanisms and theories
- Evolutionary perspectives on aging

### Theory-Specific Queries
- Mutation accumulation theory
- Antagonistic pleiotropy
- Disposable soma theory
- Free radical theory
- Mitochondrial theory of aging
- Hallmarks of aging framework

### Intervention-Based Queries
- Calorie restriction studies
- Pharmacological interventions
- Lifestyle and environmental factors

### Model Organism Queries
- C. elegans aging research
- Drosophila longevity studies
- Mouse aging models

**Complete Query Library**: See `data/queries_used.json` for the full collection of AI-generated queries covering 40+ specific aging theories and frameworks.

## Technical Architecture

### Performance Features
- **Parallel Processing**: Multi-threaded paper processing for efficiency
- **Intelligent Caching**: Prevents redundant API calls
- **Rate Limiting**: Respects API limits with exponential backoff
- **Error Recovery**: Robust handling of network and API issues

### Data Quality Assurance
- **DOI Validation**: Ensures data integrity and prevents duplicates
- **Content Verification**: Validates full-text availability and quality
- **Source Tracking**: Maintains complete data provenance
- **Quality Metrics**: Comprehensive statistics on collection success

### Reproducibility
- **Virtual Environment**: Isolated Python environment with pinned dependencies
- **Complete Logging**: Detailed execution logs for debugging and analysis
- **Version Control**: Git-based tracking of all changes and configurations
- **Documentation**: Comprehensive setup and usage instructions

## Usage Examples

### Basic Collection
```bash
python scripts/run_full.py \
  --queries "(\"aging\"[tiab] AND theory[tiab])" \
  --query-run-name "aging_theories" \
  --max-results 5000
```

### Advanced Collection with Custom Parameters
```bash
python scripts/run_full.py \
  --queries "(\"hallmarks of aging\"[tiab])" "(\"senescence\"[tiab] AND mechanism[tiab])" \
  --queries-suffix "AND (Aging[MeSH] OR Geriatrics[MeSH])" \
  --query-run-name "comprehensive_study" \
  --max-results 10000 \
  --output-dir /path/to/custom/output
```

### Test Database Mode
```bash
python scripts/run_full.py \
  --queries "(\"calorie restriction\"[tiab] AND aging[tiab])" \
  --query-run-name "intervention_study" \
  --test-db \
  --max-results 1000
```

## Project Structure

```
download_papers_pubmed/
├── src/                          # Core modules
│   ├── pubmed_extractor.py      # PubMed API integration
│   ├── openalex_extractor.py    # OpenAlex enrichment
│   ├── database.py              # SQLite operations
│   └── models.py                # Data models
├── scripts/                      # Execution scripts
│   ├── run_full.py              # Main collection script
│   └── demo.py                  # Demonstration script
├── data/                         # Query definitions
│   └── queries_used.json        # AI-generated queries
├── paper_collection/            # Main output directory
├── paper_collection_test/       # Test database output
└── requirements.txt             # Dependencies
```

## Next Steps

This collection system represents the foundation for subsequent analysis phases:

1. **Text Analysis**: Natural language processing of collected abstracts and full-text
2. **Theory Classification**: Machine learning-based categorization of aging theories
3. **Trend Analysis**: Temporal analysis of theoretical developments
4. **Network Analysis**: Citation and co-occurrence analysis of theoretical concepts

## Dependencies

- Python 3.8+
- biopython==1.83
- requests==2.31.0
- tqdm==4.66.1
- beautifulsoup4==4.12.2
- PyPDF2==3.0.1
- lxml>=4.6.0
- jsonschema>=4.0.0

See `requirements.txt` for complete dependency list with version specifications.