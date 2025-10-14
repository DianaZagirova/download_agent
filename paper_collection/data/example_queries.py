#!/usr/bin/env python3
"""
Example queries for investigating papers.db

This script demonstrates various SQL queries to explore and analyze
the paper collection database.

Database Schema:
- papers: Main table with paper metadata
- collection_runs: Statistics from collection runs
- failed_dois: Papers that couldn't get full text from PMC

Papers table fields:
- pmid, pmcid, doi, title, abstract
- full_text, full_text_sections (JSON)
- mesh_terms (JSON array), keywords (JSON array), authors (JSON array)
- year, date_published, journal
- is_full_text_pmc (boolean), openalex_retrieved (boolean)
- oa_url, primary_topic (JSON), topic_name, topic_subfield, topic_field, topic_domain
- citation_normalized_percentile, cited_by_count, fwci
- collection_date
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter

# Database path
DB_PATH = Path(__file__).parent / "papers.db"


def connect_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Create database connection with Row factory for dict-like access"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ==============================================================================
# QUERY 1: Get all unique mesh_terms for all papers
# ==============================================================================

def get_all_unique_mesh_terms() -> List[str]:
    """
    Extract all unique MeSH terms across all papers.
    
    Returns:
        Sorted list of unique MeSH terms
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    # Get all mesh_terms (stored as JSON arrays)
    cursor.execute("SELECT mesh_terms FROM papers WHERE mesh_terms IS NOT NULL")
    
    all_mesh_terms = set()
    for row in cursor.fetchall():
        if row['mesh_terms']:
            mesh_terms = json.loads(row['mesh_terms'])
            all_mesh_terms.update(mesh_terms)
    
    conn.close()
    
    unique_terms = sorted(list(all_mesh_terms))
    print(f"Total unique MeSH terms: {len(unique_terms)}")
    print("\nFirst 10 MeSH terms:")
    for term in unique_terms[:10]:
        print(f"  - {term}")
    
    return unique_terms


# ==============================================================================
# QUERY 2: Count papers by MeSH term frequency
# ==============================================================================

def get_mesh_term_frequency(top_n: int = 20) -> List[tuple]:
    """
    Count frequency of each MeSH term across all papers.
    
    Args:
        top_n: Number of top terms to return
        
    Returns:
        List of (term, count) tuples sorted by frequency
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT mesh_terms FROM papers WHERE mesh_terms IS NOT NULL")
    
    mesh_counter = Counter()
    for row in cursor.fetchall():
        if row['mesh_terms']:
            mesh_terms = json.loads(row['mesh_terms'])
            mesh_counter.update(mesh_terms)
    
    conn.close()
    
    top_terms = mesh_counter.most_common(top_n)
    print(f"\nTop {top_n} most frequent MeSH terms:")
    for term, count in top_terms:
        print(f"  {count:5d} papers: {term}")
    
    return top_terms


# ==============================================================================
# QUERY 3: Database statistics overview
# ==============================================================================

def get_database_overview() -> Dict[str, Any]:
    """
    Get comprehensive database statistics.
    
    Returns:
        Dictionary with various statistics
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    stats = {}
    
    # Total papers
    cursor.execute("SELECT COUNT(*) as count FROM papers")
    stats['total_papers'] = cursor.fetchone()['count']
    
    # Papers with full text
    cursor.execute("SELECT COUNT(*) as count FROM papers WHERE is_full_text_pmc = 1")
    stats['with_fulltext'] = cursor.fetchone()['count']
    
    # Papers without full text
    cursor.execute("SELECT COUNT(*) as count FROM papers WHERE is_full_text_pmc = 0")
    stats['without_fulltext'] = cursor.fetchone()['count']
    
    # Papers with OpenAlex data
    cursor.execute("SELECT COUNT(*) as count FROM papers WHERE openalex_retrieved = 1")
    stats['with_openalex'] = cursor.fetchone()['count']
    
    # Papers with DOI
    cursor.execute("SELECT COUNT(*) as count FROM papers WHERE doi IS NOT NULL AND doi != ''")
    stats['with_doi'] = cursor.fetchone()['count']
    
    # Papers with PMCID
    cursor.execute("SELECT COUNT(*) as count FROM papers WHERE pmcid IS NOT NULL AND pmcid != ''")
    stats['with_pmcid'] = cursor.fetchone()['count']
    
    # Papers with abstract
    cursor.execute("SELECT COUNT(*) as count FROM papers WHERE abstract IS NOT NULL AND abstract != ''")
    stats['with_abstract'] = cursor.fetchone()['count']
    
    # Papers with MeSH terms
    cursor.execute("SELECT COUNT(*) as count FROM papers WHERE mesh_terms IS NOT NULL AND mesh_terms != '[]'")
    stats['with_mesh_terms'] = cursor.fetchone()['count']
    
    # Papers with keywords
    cursor.execute("SELECT COUNT(*) as count FROM papers WHERE keywords IS NOT NULL AND keywords != '[]'")
    stats['with_keywords'] = cursor.fetchone()['count']
    
    # Year range
    cursor.execute("SELECT MIN(year) as min_year, MAX(year) as max_year FROM papers WHERE year IS NOT NULL")
    year_row = cursor.fetchone()
    stats['year_range'] = (year_row['min_year'], year_row['max_year'])
    
    conn.close()
    
    print("\n" + "="*70)
    print("DATABASE OVERVIEW")
    print("="*70)
    print(f"Total papers:              {stats['total_papers']:,}")
    print(f"With full text (PMC):      {stats['with_fulltext']:,} ({stats['with_fulltext']/stats['total_papers']*100:.1f}%)")
    print(f"Without full text:         {stats['without_fulltext']:,} ({stats['without_fulltext']/stats['total_papers']*100:.1f}%)")
    print(f"With OpenAlex data:        {stats['with_openalex']:,} ({stats['with_openalex']/stats['total_papers']*100:.1f}%)")
    print(f"With DOI:                  {stats['with_doi']:,} ({stats['with_doi']/stats['total_papers']*100:.1f}%)")
    print(f"With PMCID:                {stats['with_pmcid']:,} ({stats['with_pmcid']/stats['total_papers']*100:.1f}%)")
    print(f"With abstract:             {stats['with_abstract']:,} ({stats['with_abstract']/stats['total_papers']*100:.1f}%)")
    print(f"With MeSH terms:           {stats['with_mesh_terms']:,} ({stats['with_mesh_terms']/stats['total_papers']*100:.1f}%)")
    print(f"With keywords:             {stats['with_keywords']:,} ({stats['with_keywords']/stats['total_papers']*100:.1f}%)")
    print(f"Year range:                {stats['year_range'][0]} - {stats['year_range'][1]}")
    print("="*70)
    
    return stats


# ==============================================================================
# QUERY 4: Top journals
# ==============================================================================

def get_top_journals(top_n: int = 20) -> List[tuple]:
    """
    Get the most common journals in the collection.
    
    Args:
        top_n: Number of top journals to return
        
    Returns:
        List of (journal, count) tuples
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT journal, COUNT(*) as count 
        FROM papers 
        WHERE journal IS NOT NULL AND journal != ''
        GROUP BY journal 
        ORDER BY count DESC 
        LIMIT ?
    """, (top_n,))
    
    results = [(row['journal'], row['count']) for row in cursor.fetchall()]
    conn.close()
    
    print(f"\nTop {top_n} journals:")
    for journal, count in results:
        print(f"  {count:5d} papers: {journal}")
    
    return results


# ==============================================================================
# QUERY 5: Papers by year
# ==============================================================================

def get_papers_by_year() -> Dict[str, int]:
    """
    Count papers by publication year.
    
    Returns:
        Dictionary of year -> count
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT year, COUNT(*) as count 
        FROM papers 
        WHERE year IS NOT NULL 
        GROUP BY year 
        ORDER BY year DESC
    """)
    
    results = {row['year']: row['count'] for row in cursor.fetchall()}
    conn.close()
    
    print("\nPapers by year:")
    for year, count in sorted(results.items(), reverse=True):
        print(f"  {year}: {count:5d} papers")
    
    return results


# ==============================================================================
# QUERY 6: OpenAlex topic analysis
# ==============================================================================

def get_top_topics(top_n: int = 20) -> List[tuple]:
    """
    Get the most common research topics from OpenAlex data.
    
    Args:
        top_n: Number of top topics to return
        
    Returns:
        List of (topic_name, count) tuples
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT topic_name, COUNT(*) as count 
        FROM papers 
        WHERE topic_name IS NOT NULL 
        GROUP BY topic_name 
        ORDER BY count DESC 
        LIMIT ?
    """, (top_n,))
    
    results = [(row['topic_name'], row['count']) for row in cursor.fetchall()]
    conn.close()
    
    print(f"\nTop {top_n} research topics:")
    for topic, count in results:
        print(f"  {count:5d} papers: {topic}")
    
    return results


# ==============================================================================
# QUERY 7: Topic hierarchy analysis
# ==============================================================================

def get_topic_hierarchy_stats() -> Dict[str, Dict[str, int]]:
    """
    Analyze the hierarchical structure of topics (domain -> field -> subfield -> topic).
    
    Returns:
        Dictionary with counts at each level
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    stats = {}
    
    # Domains
    cursor.execute("""
        SELECT topic_domain, COUNT(*) as count 
        FROM papers 
        WHERE topic_domain IS NOT NULL 
        GROUP BY topic_domain 
        ORDER BY count DESC
    """)
    stats['domains'] = {row['topic_domain']: row['count'] for row in cursor.fetchall()}
    
    # Fields
    cursor.execute("""
        SELECT topic_field, COUNT(*) as count 
        FROM papers 
        WHERE topic_field IS NOT NULL 
        GROUP BY topic_field 
        ORDER BY count DESC 
        LIMIT 20
    """)
    stats['fields'] = {row['topic_field']: row['count'] for row in cursor.fetchall()}
    
    # Subfields
    cursor.execute("""
        SELECT topic_subfield, COUNT(*) as count 
        FROM papers 
        WHERE topic_subfield IS NOT NULL 
        GROUP BY topic_subfield 
        ORDER BY count DESC 
        LIMIT 20
    """)
    stats['subfields'] = {row['topic_subfield']: row['count'] for row in cursor.fetchall()}
    
    conn.close()
    
    print("\nTopic Hierarchy Analysis:")
    print("\nTop Domains:")
    for domain, count in stats['domains'].items():
        print(f"  {count:5d} papers: {domain}")
    
    print("\nTop Fields (top 20):")
    for field, count in stats['fields'].items():
        print(f"  {count:5d} papers: {field}")
    
    print("\nTop Subfields (top 20):")
    for subfield, count in stats['subfields'].items():
        print(f"  {count:5d} papers: {subfield}")
    
    return stats


# ==============================================================================
# QUERY 8: Citation metrics analysis
# ==============================================================================

def get_citation_stats() -> Dict[str, Any]:
    """
    Analyze citation metrics (cited_by_count, FWCI, percentile).
    
    Returns:
        Dictionary with citation statistics
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    stats = {}
    
    # Papers with citation data
    cursor.execute("SELECT COUNT(*) as count FROM papers WHERE cited_by_count IS NOT NULL")
    stats['with_citations'] = cursor.fetchone()['count']
    
    # Citation statistics
    cursor.execute("""
        SELECT 
            AVG(cited_by_count) as avg_citations,
            MAX(cited_by_count) as max_citations,
            MIN(cited_by_count) as min_citations
        FROM papers 
        WHERE cited_by_count IS NOT NULL
    """)
    row = cursor.fetchone()
    stats['avg_citations'] = row['avg_citations']
    stats['max_citations'] = row['max_citations']
    stats['min_citations'] = row['min_citations']
    
    # FWCI statistics
    cursor.execute("""
        SELECT 
            AVG(fwci) as avg_fwci,
            MAX(fwci) as max_fwci,
            MIN(fwci) as min_fwci
        FROM papers 
        WHERE fwci IS NOT NULL
    """)
    row = cursor.fetchone()
    stats['avg_fwci'] = row['avg_fwci']
    stats['max_fwci'] = row['max_fwci']
    stats['min_fwci'] = row['min_fwci']
    
    # Percentile statistics
    cursor.execute("""
        SELECT 
            AVG(citation_normalized_percentile) as avg_percentile,
            MAX(citation_normalized_percentile) as max_percentile,
            MIN(citation_normalized_percentile) as min_percentile
        FROM papers 
        WHERE citation_normalized_percentile IS NOT NULL
    """)
    row = cursor.fetchone()
    stats['avg_percentile'] = row['avg_percentile']
    stats['max_percentile'] = row['max_percentile']
    stats['min_percentile'] = row['min_percentile']
    
    # Top cited papers
    cursor.execute("""
        SELECT pmid, title, cited_by_count, fwci, citation_normalized_percentile
        FROM papers 
        WHERE cited_by_count IS NOT NULL
        ORDER BY cited_by_count DESC
        LIMIT 10
    """)
    stats['top_cited'] = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    print("\nCitation Metrics Analysis:")
    print(f"Papers with citation data: {stats['with_citations']:,}")
    print(f"\nCitation counts:")
    print(f"  Average: {stats['avg_citations']:.2f}")
    print(f"  Maximum: {stats['max_citations']}")
    print(f"  Minimum: {stats['min_citations']}")
    print(f"\nFWCI (Field-Weighted Citation Impact):")
    print(f"  Average: {stats['avg_fwci']:.3f}")
    print(f"  Maximum: {stats['max_fwci']:.3f}")
    print(f"  Minimum: {stats['min_fwci']:.3f}")
    print(f"\nCitation Normalized Percentile:")
    print(f"  Average: {stats['avg_percentile']:.2f}")
    print(f"  Maximum: {stats['max_percentile']:.2f}")
    print(f"  Minimum: {stats['min_percentile']:.2f}")
    
    print("\nTop 10 most cited papers:")
    for i, paper in enumerate(stats['top_cited'], 1):
        title = paper['title'][:60] + '...' if len(paper['title']) > 60 else paper['title']
        print(f"  {i}. [{paper['cited_by_count']:5d} citations] {title}")
        print(f"     PMID: {paper['pmid']}, FWCI: {paper['fwci']:.2f}, Percentile: {paper['citation_normalized_percentile']:.1f}")
    
    return stats


# ==============================================================================
# QUERY 9: Search papers by specific MeSH term
# ==============================================================================

def search_by_mesh_term(mesh_term: str) -> List[Dict]:
    """
    Find all papers tagged with a specific MeSH term.
    
    Args:
        mesh_term: MeSH term to search for
        
    Returns:
        List of paper dictionaries
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM papers WHERE mesh_terms IS NOT NULL")
    
    matching_papers = []
    for row in cursor.fetchall():
        if row['mesh_terms']:
            mesh_terms = json.loads(row['mesh_terms'])
            if mesh_term in mesh_terms:
                matching_papers.append(dict(row))
    
    conn.close()
    
    print(f"\nFound {len(matching_papers)} papers with MeSH term '{mesh_term}'")
    
    # Show first 5
    for i, paper in enumerate(matching_papers[:5], 1):
        title = paper['title'][:60] + '...' if paper['title'] and len(paper['title']) > 60 else paper['title']
        print(f"  {i}. {title}")
        print(f"     PMID: {paper['pmid']}, Year: {paper['year']}, Journal: {paper['journal']}")
    
    if len(matching_papers) > 5:
        print(f"  ... and {len(matching_papers) - 5} more")
    
    return matching_papers


# ==============================================================================
# QUERY 9B: Get DOIs by MeSH term
# ==============================================================================

def get_dois_by_mesh_term(mesh_term: str) -> List[str]:
    """
    Get all DOIs for papers with a specific MeSH term.
    
    Args:
        mesh_term: MeSH term to search for
        
    Returns:
        List of DOIs (excluding papers without DOIs)
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT doi, pmid, title, mesh_terms FROM papers WHERE mesh_terms IS NOT NULL")
    
    dois = []
    for row in cursor.fetchall():
        if row['mesh_terms']:
            mesh_terms = json.loads(row['mesh_terms'])
            if mesh_term in mesh_terms:
                if row['doi']:  # Only include papers with DOIs
                    dois.append(row['doi'])
    
    conn.close()
    
    print(f"\nFound {len(dois)} papers with MeSH term '{mesh_term}' that have DOIs")
    print("\nFirst 10 DOIs:")
    for doi in dois[:10]:
        print(f"  {doi}")
    
    if len(dois) > 10:
        print(f"  ... and {len(dois) - 10} more")
    
    return dois


# ==============================================================================
# QUERY 10: Full text content analysis
# ==============================================================================

def analyze_full_text_content() -> Dict[str, Any]:
    """
    Analyze full text content - section availability, text length, etc.
    
    Returns:
        Dictionary with full text statistics
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    stats = {}
    
    # Papers with full_text_sections
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM papers 
        WHERE full_text_sections IS NOT NULL AND full_text_sections != '{}'
    """)
    stats['with_sections'] = cursor.fetchone()['count']
    
    # Papers with flat full_text
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM papers 
        WHERE full_text IS NOT NULL AND full_text != ''
    """)
    stats['with_flat_text'] = cursor.fetchone()['count']
    
    # Analyze section names
    cursor.execute("""
        SELECT full_text_sections 
        FROM papers 
        WHERE full_text_sections IS NOT NULL AND full_text_sections != '{}'
    """)
    
    section_counter = Counter()
    for row in cursor.fetchall():
        if row['full_text_sections']:
            sections = json.loads(row['full_text_sections'])
            # Handle both dict and list formats
            if isinstance(sections, dict):
                section_counter.update(sections.keys())
            elif isinstance(sections, list):
                # If it's a list, we can't extract section names
                pass
    
    stats['common_sections'] = section_counter.most_common(20)
    
    # Average text length for papers with full text
    cursor.execute("""
        SELECT AVG(LENGTH(full_text)) as avg_length
        FROM papers 
        WHERE full_text IS NOT NULL AND full_text != ''
    """)
    stats['avg_text_length'] = cursor.fetchone()['avg_length']
    
    conn.close()
    
    print("\nFull Text Content Analysis:")
    print(f"Papers with sectioned full text: {stats['with_sections']:,}")
    print(f"Papers with flat full text:      {stats['with_flat_text']:,}")
    print(f"Average text length:             {stats['avg_text_length']:,.0f} characters")
    
    print("\nMost common section names:")
    for section, count in stats['common_sections']:
        print(f"  {count:5d} papers: {section}")
    
    return stats


# ==============================================================================
# QUERY 11: Author analysis
# ==============================================================================

def get_top_authors(top_n: int = 20) -> List[tuple]:
    """
    Find the most prolific authors in the collection.
    
    Args:
        top_n: Number of top authors to return
        
    Returns:
        List of (author, count) tuples
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT authors FROM papers WHERE authors IS NOT NULL AND authors != '[]'")
    
    author_counter = Counter()
    for row in cursor.fetchall():
        if row['authors']:
            authors = json.loads(row['authors'])
            author_counter.update(authors)
    
    conn.close()
    
    top_authors = author_counter.most_common(top_n)
    print(f"\nTop {top_n} most prolific authors:")
    for author, count in top_authors:
        print(f"  {count:5d} papers: {author}")
    
    return top_authors


# ==============================================================================
# QUERY 12: Collection timeline
# ==============================================================================

def get_collection_timeline() -> List[Dict]:
    """
    Analyze when papers were collected.
    
    Returns:
        List of collection run statistics
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM collection_runs 
        ORDER BY start_time DESC
    """)
    
    runs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    print(f"\nFound {len(runs)} collection runs:")
    for i, run in enumerate(runs, 1):
        print(f"\n  Run {i} (ID: {run['id']}):")
        print(f"    Query: {run['query'][:70]}...")
        print(f"    Start: {run['start_time']}")
        print(f"    Total processed: {run['total_processed']}")
        print(f"    With full text:  {run['with_full_text']}")
        print(f"    With OpenAlex:   {run['with_openalex']}")
    
    return runs


# ==============================================================================
# QUERY 13: Advanced search - combine multiple filters
# ==============================================================================

def advanced_search(
    mesh_term: str = None,
    topic_field: str = None,
    min_citations: int = None,
    year_from: str = None,
    year_to: str = None,
    has_fulltext: bool = None,
    limit: int = 100
) -> List[Dict]:
    """
    Advanced search with multiple filters.
    
    Args:
        mesh_term: Filter by MeSH term
        topic_field: Filter by OpenAlex topic field
        min_citations: Minimum citation count
        year_from: Starting year
        year_to: Ending year
        has_fulltext: Filter by full text availability
        limit: Maximum results to return
        
    Returns:
        List of matching papers
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    # Build query dynamically
    query = "SELECT * FROM papers WHERE 1=1"
    params = []
    
    if topic_field:
        query += " AND topic_field = ?"
        params.append(topic_field)
    
    if min_citations:
        query += " AND cited_by_count >= ?"
        params.append(min_citations)
    
    if year_from:
        query += " AND year >= ?"
        params.append(year_from)
    
    if year_to:
        query += " AND year <= ?"
        params.append(year_to)
    
    if has_fulltext is not None:
        query += " AND is_full_text_pmc = ?"
        params.append(1 if has_fulltext else 0)
    
    query += f" LIMIT {limit}"
    
    cursor.execute(query, params)
    results = []
    
    for row in cursor.fetchall():
        paper = dict(row)
        
        # Apply MeSH term filter if specified (can't do in SQL easily)
        if mesh_term:
            if paper['mesh_terms']:
                mesh_terms = json.loads(paper['mesh_terms'])
                if mesh_term not in mesh_terms:
                    continue
        
        results.append(paper)
    
    conn.close()
    
    print(f"\nAdvanced search found {len(results)} papers:")
    print(f"  Filters: mesh_term={mesh_term}, topic_field={topic_field}, "
          f"min_citations={min_citations}, year={year_from}-{year_to}, "
          f"has_fulltext={has_fulltext}")
    
    for i, paper in enumerate(results[:10], 1):
        title = paper['title'][:60] + '...' if paper['title'] and len(paper['title']) > 60 else paper['title']
        print(f"  {i}. {title}")
        print(f"     PMID: {paper['pmid']}, Year: {paper['year']}, Citations: {paper['cited_by_count']}")
    
    if len(results) > 10:
        print(f"  ... and {len(results) - 10} more")
    
    return results


# ==============================================================================
# QUERY 14: Get papers and DOIs by query ID
# ==============================================================================

def get_papers_by_query_id(query_id: int = None) -> Dict[str, Any]:
    """
    Get papers collected with a specific query.
    
    Args:
        query_id: Query ID (if None, shows all queries)
        
    Returns:
        Dictionary with query info and papers
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    # If no query_id specified, show all queries
    if query_id is None:
        cursor.execute("SELECT id, description, created_date FROM queries ORDER BY id")
        queries = cursor.fetchall()
        
        print("\nAvailable queries:")
        for row in queries:
            cursor.execute("SELECT COUNT(*) FROM papers WHERE query_id = ?", (row['id'],))
            count = cursor.fetchone()[0]
            print(f"\n  Query ID: {row['id']}")
            print(f"  Description: {row['description']}")
            print(f"  Papers: {count}")
        
        conn.close()
        return {'queries': [dict(q) for q in queries]}
    
    # Get query details
    cursor.execute("SELECT * FROM queries WHERE id = ?", (query_id,))
    query = cursor.fetchone()
    
    if not query:
        print(f"Query ID {query_id} not found")
        conn.close()
        return {}
    
    # Get papers for this query
    cursor.execute("SELECT pmid, doi, title, year, journal FROM papers WHERE query_id = ?", (query_id,))
    papers = [dict(row) for row in cursor.fetchall()]
    
    # Get DOIs (excluding None)
    dois = [p['doi'] for p in papers if p['doi']]
    
    conn.close()
    
    print(f"\nQuery ID: {query['id']}")
    print(f"Description: {query['description']}")
    print(f"Created: {query['created_date']}")
    print(f"\nTotal papers: {len(papers)}")
    print(f"Papers with DOIs: {len(dois)}")
    
    print("\nFirst 10 papers:")
    for i, paper in enumerate(papers[:10], 1):
        title = paper['title'][:60] + '...' if paper['title'] and len(paper['title']) > 60 else paper['title']
        print(f"  {i}. {title}")
        print(f"     PMID: {paper['pmid']}, DOI: {paper['doi']}, Year: {paper['year']}")
    
    if len(papers) > 10:
        print(f"  ... and {len(papers) - 10} more")
    
    return {
        'query': dict(query),
        'papers': papers,
        'dois': dois
    }


def get_dois_by_query_and_mesh(query_id: int, mesh_term: str) -> List[str]:
    """
    Get DOIs for papers that match both a query_id and a MeSH term.
    
    Args:
        query_id: Query ID
        mesh_term: MeSH term to filter by
        
    Returns:
        List of DOIs
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT doi, pmid, title, mesh_terms 
        FROM papers 
        WHERE query_id = ? AND mesh_terms IS NOT NULL
    """, (query_id,))
    
    dois = []
    for row in cursor.fetchall():
        if row['mesh_terms']:
            mesh_terms = json.loads(row['mesh_terms'])
            if mesh_term in mesh_terms and row['doi']:
                dois.append(row['doi'])
    
    conn.close()
    
    print(f"\nFound {len(dois)} papers with query_id={query_id} AND MeSH term '{mesh_term}' that have DOIs")
    print("\nFirst 10 DOIs:")
    for doi in dois[:10]:
        print(f"  {doi}")
    
    if len(dois) > 10:
        print(f"  ... and {len(dois) - 10} more")
    
    return dois


# ==============================================================================
# MAIN: Run example queries
# ==============================================================================

def main():
    """Run all example queries"""
    
    print("\n" + "#"*70)
    print("# EXAMPLE QUERIES FOR papers.db")
    print("#"*70)
    
    # 1. Get all unique mesh terms
    print("\n" + "="*70)
    print("QUERY 1: Get all unique MeSH terms")
    print("="*70)
    get_all_unique_mesh_terms()
    
    # 2. MeSH term frequency
    print("\n" + "="*70)
    print("QUERY 2: MeSH term frequency")
    print("="*70)
    get_mesh_term_frequency(top_n=20)
    
    # 3. Database overview
    print("\n" + "="*70)
    print("QUERY 3: Database overview")
    print("="*70)
    get_database_overview()
    
    # 4. Top journals
    print("\n" + "="*70)
    print("QUERY 4: Top journals")
    print("="*70)
    get_top_journals(top_n=20)
    
    # 5. Papers by year
    print("\n" + "="*70)
    print("QUERY 5: Papers by year")
    print("="*70)
    get_papers_by_year()
    
    # 6. Top topics
    print("\n" + "="*70)
    print("QUERY 6: Top research topics")
    print("="*70)
    get_top_topics(top_n=20)
    
    # 7. Topic hierarchy
    print("\n" + "="*70)
    print("QUERY 7: Topic hierarchy analysis")
    print("="*70)
    get_topic_hierarchy_stats()
    
    # 8. Citation metrics
    print("\n" + "="*70)
    print("QUERY 8: Citation metrics")
    print("="*70)
    get_citation_stats()
    
    # 9. Full text analysis
    print("\n" + "="*70)
    print("QUERY 10: Full text content analysis")
    print("="*70)
    analyze_full_text_content()
    
    # 10. Top authors
    print("\n" + "="*70)
    print("QUERY 11: Top authors")
    print("="*70)
    get_top_authors(top_n=20)
    
    # 11. Collection timeline
    print("\n" + "="*70)
    print("QUERY 12: Collection timeline")
    print("="*70)
    get_collection_timeline()
    
    print("\n" + "#"*70)
    print("# Example queries completed!")
    print("#"*70)


if __name__ == "__main__":
    main()
