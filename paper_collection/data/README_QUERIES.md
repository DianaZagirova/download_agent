# Example Queries for papers.db

This document provides examples of how to query and analyze the `papers.db` SQLite database using Python.

## Quick Start

Run all example queries:
```bash
python example_queries.py
```

Or import specific functions in your own scripts:
```python
from example_queries import get_all_unique_mesh_terms, get_database_overview

# Get unique MeSH terms
mesh_terms = get_all_unique_mesh_terms()

# Get database statistics
stats = get_database_overview()
```

---

## Database Schema

### Tables

#### `papers` - Main table with paper metadata
- **Basic identifiers**: `pmid`, `pmcid`, `doi`
- **Content**: `title`, `abstract`, `full_text`, `full_text_sections` (JSON)
- **Metadata**: `mesh_terms` (JSON array), `keywords` (JSON array), `authors` (JSON array)
- **Publication info**: `year`, `date_published`, `journal`
- **OpenAlex data**: `oa_url`, `primary_topic` (JSON), `topic_name`, `topic_subfield`, `topic_field`, `topic_domain`
- **Citation metrics**: `citation_normalized_percentile`, `cited_by_count`, `fwci`
- **Flags**: `is_full_text_pmc` (boolean), `openalex_retrieved` (boolean)
- **System**: `collection_date`

#### `collection_runs` - Statistics from collection runs
- `id`, `query`, `total_found`, `total_processed`, `with_full_text`, `without_full_text`
- `with_openalex`, `failed_pubmed`, `failed_openalex`, `start_time`, `end_time`

#### `failed_dois` - Papers that couldn't get full text from PMC
- `doi`, `pmid`, `reason`, `timestamp`

---

## Available Query Functions

### 1. Get All Unique MeSH Terms
Extract all unique MeSH terms across all papers.

```python
from example_queries import get_all_unique_mesh_terms

mesh_terms = get_all_unique_mesh_terms()
# Returns: List of unique MeSH terms (sorted)
```

**Direct SQL:**
```python
import sqlite3
import json

conn = sqlite3.connect('papers.db')
cursor = conn.cursor()
cursor.execute("SELECT mesh_terms FROM papers WHERE mesh_terms IS NOT NULL")

all_mesh_terms = set()
for row in cursor.fetchall():
    if row[0]:
        mesh_terms = json.loads(row[0])
        all_mesh_terms.update(mesh_terms)

unique_terms = sorted(list(all_mesh_terms))
```

---

### 2. MeSH Term Frequency
Count how often each MeSH term appears across papers.

```python
from example_queries import get_mesh_term_frequency

top_terms = get_mesh_term_frequency(top_n=20)
# Returns: List of (term, count) tuples
```

---

### 3. Database Overview
Get comprehensive database statistics.

```python
from example_queries import get_database_overview

stats = get_database_overview()
# Returns: Dictionary with various statistics
```

**Statistics included:**
- Total papers
- Papers with/without full text
- Papers with OpenAlex data
- Papers with DOI, PMCID, abstracts, MeSH terms, keywords
- Year range

---

### 4. Top Journals
Find the most common journals in the collection.

```python
from example_queries import get_top_journals

journals = get_top_journals(top_n=20)
# Returns: List of (journal, count) tuples
```

**Direct SQL:**
```sql
SELECT journal, COUNT(*) as count 
FROM papers 
WHERE journal IS NOT NULL AND journal != ''
GROUP BY journal 
ORDER BY count DESC 
LIMIT 20;
```

---

### 5. Papers by Year
Count papers by publication year.

```python
from example_queries import get_papers_by_year

year_counts = get_papers_by_year()
# Returns: Dictionary of year -> count
```

**Direct SQL:**
```sql
SELECT year, COUNT(*) as count 
FROM papers 
WHERE year IS NOT NULL 
GROUP BY year 
ORDER BY year DESC;
```

---

### 6. Top Research Topics
Get the most common research topics from OpenAlex data.

```python
from example_queries import get_top_topics

topics = get_top_topics(top_n=20)
# Returns: List of (topic_name, count) tuples
```

---

### 7. Topic Hierarchy Analysis
Analyze the hierarchical structure of topics (domain → field → subfield → topic).

```python
from example_queries import get_topic_hierarchy_stats

hierarchy = get_topic_hierarchy_stats()
# Returns: Dictionary with 'domains', 'fields', 'subfields' keys
```

**Direct SQL examples:**
```sql
-- Top domains
SELECT topic_domain, COUNT(*) as count 
FROM papers 
WHERE topic_domain IS NOT NULL 
GROUP BY topic_domain 
ORDER BY count DESC;

-- Top fields
SELECT topic_field, COUNT(*) as count 
FROM papers 
WHERE topic_field IS NOT NULL 
GROUP BY topic_field 
ORDER BY count DESC 
LIMIT 20;
```

---

### 8. Citation Metrics Analysis
Analyze citation metrics (cited_by_count, FWCI, percentile).

```python
from example_queries import get_citation_stats

citation_stats = get_citation_stats()
# Returns: Dictionary with citation statistics and top cited papers
```

**Statistics included:**
- Papers with citation data
- Average/max/min citation counts
- FWCI (Field-Weighted Citation Impact) statistics
- Citation normalized percentile statistics
- Top 10 most cited papers

**Direct SQL:**
```sql
-- Average citation metrics
SELECT 
    AVG(cited_by_count) as avg_citations,
    AVG(fwci) as avg_fwci,
    AVG(citation_normalized_percentile) as avg_percentile
FROM papers 
WHERE cited_by_count IS NOT NULL;

-- Top cited papers
SELECT pmid, title, cited_by_count, fwci, citation_normalized_percentile
FROM papers 
WHERE cited_by_count IS NOT NULL
ORDER BY cited_by_count DESC
LIMIT 10;
```

---

### 9. Search by MeSH Term
Find all papers tagged with a specific MeSH term.

```python
from example_queries import search_by_mesh_term

papers = search_by_mesh_term("Aging")
# Returns: List of paper dictionaries
```

**Note:** MeSH terms are stored as JSON arrays, so we need to parse them:
```python
import json

conn = sqlite3.connect('papers.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM papers WHERE mesh_terms IS NOT NULL")

matching_papers = []
for row in cursor.fetchall():
    if row['mesh_terms']:
        mesh_terms = json.loads(row['mesh_terms'])
        if "Aging" in mesh_terms:
            matching_papers.append(dict(row))
```

---

### 10. Full Text Content Analysis
Analyze full text content - section availability, text length, etc.

```python
from example_queries import analyze_full_text_content

text_stats = analyze_full_text_content()
# Returns: Dictionary with full text statistics
```

**Statistics included:**
- Papers with sectioned full text
- Papers with flat full text
- Average text length
- Most common section names

---

### 11. Top Authors
Find the most prolific authors in the collection.

```python
from example_queries import get_top_authors

authors = get_top_authors(top_n=20)
# Returns: List of (author, count) tuples
```

---

### 12. Collection Timeline
Analyze when papers were collected.

```python
from example_queries import get_collection_timeline

runs = get_collection_timeline()
# Returns: List of collection run statistics
```

**Direct SQL:**
```sql
SELECT * FROM collection_runs 
ORDER BY start_time DESC;
```

---

### 13. Advanced Search
Combine multiple filters to find specific papers.

```python
from example_queries import advanced_search

# Example: Find highly cited papers about aging from 2010-2020
papers = advanced_search(
    mesh_term="Aging",
    topic_field="Biochemistry, Genetics and Molecular Biology",
    min_citations=100,
    year_from="2010",
    year_to="2020",
    has_fulltext=True,
    limit=100
)
# Returns: List of matching papers
```

**Filter options:**
- `mesh_term`: Filter by specific MeSH term
- `topic_field`: Filter by OpenAlex topic field
- `min_citations`: Minimum citation count
- `year_from`: Starting year
- `year_to`: Ending year
- `has_fulltext`: Boolean - papers with/without full text
- `limit`: Maximum results to return

---

## Common Query Patterns

### Count papers with specific criteria
```python
import sqlite3

conn = sqlite3.connect('papers.db')
cursor = conn.cursor()

# Papers published in 2024
cursor.execute("SELECT COUNT(*) FROM papers WHERE year = '2024'")
count = cursor.fetchone()[0]

# Papers with both full text and high citations
cursor.execute("""
    SELECT COUNT(*) FROM papers 
    WHERE is_full_text_pmc = 1 
    AND cited_by_count > 100
""")
count = cursor.fetchone()[0]
```

### Get specific papers
```python
# Get paper by PMID
cursor.execute("SELECT * FROM papers WHERE pmid = ?", ('12345678',))
paper = cursor.fetchone()

# Get papers from specific journal
cursor.execute("""
    SELECT pmid, title, year FROM papers 
    WHERE journal LIKE '%Experimental gerontology%'
    LIMIT 10
""")
papers = cursor.fetchall()
```

### Working with JSON fields
```python
import json

# Get papers and parse their MeSH terms
cursor.execute("SELECT pmid, title, mesh_terms FROM papers LIMIT 10")
for row in cursor.fetchall():
    pmid, title, mesh_terms_json = row
    if mesh_terms_json:
        mesh_terms = json.loads(mesh_terms_json)
        print(f"{pmid}: {mesh_terms}")

# Get papers and parse their full text sections
cursor.execute("SELECT pmid, full_text_sections FROM papers WHERE is_full_text_pmc = 1 LIMIT 5")
for row in cursor.fetchall():
    pmid, sections_json = row
    if sections_json:
        sections = json.loads(sections_json)
        if isinstance(sections, dict):
            print(f"{pmid} has sections: {list(sections.keys())}")
```

### Aggregation queries
```python
# Average citations by topic field
cursor.execute("""
    SELECT topic_field, 
           AVG(cited_by_count) as avg_citations,
           COUNT(*) as paper_count
    FROM papers 
    WHERE topic_field IS NOT NULL AND cited_by_count IS NOT NULL
    GROUP BY topic_field
    ORDER BY avg_citations DESC
    LIMIT 10
""")

# Papers per year with full text
cursor.execute("""
    SELECT year, 
           COUNT(*) as total_papers,
           SUM(is_full_text_pmc) as with_fulltext
    FROM papers 
    WHERE year IS NOT NULL
    GROUP BY year
    ORDER BY year DESC
""")
```

---

## Tips and Best Practices

1. **JSON Fields**: Remember that `mesh_terms`, `keywords`, `authors`, `full_text_sections`, and `primary_topic` are stored as JSON strings. Always use `json.loads()` to parse them.

2. **Boolean Fields**: `is_full_text_pmc` and `openalex_retrieved` are stored as integers (0 or 1). Use `= 1` for True and `= 0` for False.

3. **NULL Handling**: Many fields can be NULL or empty strings. Always check for both when filtering:
   ```sql
   WHERE field IS NOT NULL AND field != ''
   ```

4. **Performance**: For large queries, consider using indexes. The database already has a primary key on `pmid`.

5. **Row Factory**: Use `conn.row_factory = sqlite3.Row` to access columns by name:
   ```python
   conn = sqlite3.connect('papers.db')
   conn.row_factory = sqlite3.Row
   cursor = conn.cursor()
   cursor.execute("SELECT * FROM papers LIMIT 1")
   row = cursor.fetchone()
   print(row['title'])  # Access by column name
   ```

---

## Running Custom Queries

You can write your own queries by following this template:

```python
import sqlite3
import json
from pathlib import Path

# Connect to database
DB_PATH = Path(__file__).parent / "papers.db"
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row  # Enable column name access
cursor = conn.cursor()

# Your query here
cursor.execute("""
    SELECT pmid, title, mesh_terms, cited_by_count
    FROM papers 
    WHERE year >= '2020'
    AND cited_by_count > 50
    ORDER BY cited_by_count DESC
    LIMIT 10
""")

# Process results
for row in cursor.fetchall():
    print(f"PMID: {row['pmid']}")
    print(f"Title: {row['title']}")
    print(f"Citations: {row['cited_by_count']}")
    
    # Parse JSON field
    if row['mesh_terms']:
        mesh_terms = json.loads(row['mesh_terms'])
        print(f"MeSH terms: {', '.join(mesh_terms[:5])}")
    print()

# Close connection
conn.close()
```

---

## Database Statistics (as of latest run)

- **Total papers**: 1,145
- **With full text (PMC)**: 275 (24.0%)
- **With OpenAlex data**: 731 (63.8%)
- **Year range**: 1951 - 2025
- **Unique MeSH terms**: 1,813
- **Most common topics**: Genetics, Aging, and Longevity in Model Organisms (171 papers)

---

## Support

For more information about the database schema and data models, see:
- `/src/models.py` - PaperMetadata and CollectionStats data classes
- `/src/database.py` - PaperDatabase class with helper methods
