
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
```

### 2. Run the Demo

```bash
python demo.py
```

The demo executes three representative queries, returning roughly 150 papers and exporting:
- **SQLite database:** `paper_collection_test/data/test_papers.db`
- **JSON snapshot:** `paper_collection_test/data/test_papers_export.json`
- **Basic stats and logs:** stored under `paper_collection_test/data/`

### 3. Launch a Custom Crawl

```bash
python scripts/run_full.py \
  --queries "(\"theory of aging\"[Title]) AND (\"Aging\"[Mesh]) AND (2020:2025[dp]) AND (full text[sb])" \
  --query-run-name "recent_aging_theories" \
  --max-results 1000 \
  --test-db
```

Outputs land under `paper_collection_test/data/` in both SQLite and JSON formats, making it easy to inspect results or feed them into notebooks.

---

## 🧐 How It Works

### Top-Down Retrieval Pipeline

1. **AI- and expert-informed query generation** covers evolutionary, molecular, systems, intervention-based, and emerging aging theories while adapting synonyms and cross-domain terminology. Queries are iteratively expanded by an AI agent that reviews prior outputs to surface gaps.
2. **Iterative refinement** filters obvious false positives (for example, cosmetic dermatology) based on hit analysis and human feedback.
3. **Multi-source harvesting** gathers metadata and full records from PubMed, arXiv, medRxiv, bioRxiv, OpenAlex, and Europe PMC.
4. **Structured storage & export** normalizes data into SQLite and JSON, preserving provenance and metadata for reproducibility.

### Technical Highlights

- **Parallel multi-threaded fetching** keeps throughput high even for large query batches.
- **API-aware caching and rate limiting** minimize retries and respect provider policies.
- **Data integrity checks** validate DOIs, track provenance, and deduplicate records.
- **Reproducible runs** via pinned dependencies, structured logs, and consistent output formats.

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
├── src/
│   ├── pubmed_extractor.py
│   ├── openalex_extractor.py
│   ├── database.py
│   └── models.py
├── scripts/
│   ├── run_full.py
│   └── demo.py
├── data/
│   └── queries_used.json
├── paper_collection/
├── paper_collection_test/
└── requirements.txt
```

---

## 🛣️ CODE FOR THE NEXT STEP 

- **Stage 2:** Full-text retrieval and enrichment – see https://github.com/DianaZagirova/scihub_api

Contributions and issue reports that improve search coverage, data quality, or documentation are warmly welcomed.