# Configuration Files for run_full.py

This directory contains JSON configuration files for running paper collection queries.

## Usage

Run a collection using a config file:

```bash
python scripts/run_full.py --config config/theory_aging_2024.json
```

## Config File Format

```json
{
  "queries": [
    "query1",
    "query2"
  ],
  "queries_suffix": "optional suffix to append to all queries",
  "query_run_name": "descriptive_name_for_run",
  "use_suffix": true,
  "max_results": 10000,
  "check_num": 10000,
  "test_db": false,
  "output_dir": null,
  "description": "Human-readable description of what this config does"
}
```

## Parameters

- **queries** (required): List of PubMed search queries to execute
- **queries_suffix** (optional): String to append to all queries if `use_suffix` is true
- **query_run_name** (required): Descriptive name for the run (used in logs and output)
- **use_suffix** (optional, default: false): Whether to append `queries_suffix` to each query
- **max_results** (optional, default: 60000): Maximum number of results to collect
- **check_num** (optional, default: 60000): Number to check against for validation
- **test_db** (optional, default: false): Use test database instead of main database
- **output_dir** (optional, default: null): Custom output directory path
- **description** (optional): Human-readable description (not used by script)

## Example Configs

### theory_aging_2024.json
Search for papers with "theory of aging" in title/abstract published in 2024.

```bash
python scripts/run_full.py --config config/theory_aging_2024.json
```

### aging_theories_recent.json
Search for aging/ageing papers with theory/theories keywords in 2023-2024.

```bash
python scripts/run_full.py --config config/aging_theories_recent.json
```

## PubMed Query Syntax

Common search field tags:
- `[Title/Abstract]` or `[tiab]` - Search in title and abstract
- `[Title]` or `[ti]` - Search in title only
- `[dp]` - Date of publication (e.g., `2024[dp]` or `2023:2024[dp]`)
- `[MAJR]` - MeSH Major Topic
- `[MeSH Terms]` - MeSH terms

Boolean operators: `AND`, `OR`, `NOT`

Examples:
- `"theory of aging"[Title/Abstract] AND 2024[dp]`
- `(aging[tiab] OR ageing[tiab]) AND theory[tiab]`
- `"Aging/physiology"[MAJR] AND 2020:2024[dp]`

See [PubMed Help](https://pubmed.ncbi.nlm.nih.gov/help/) for more details.
