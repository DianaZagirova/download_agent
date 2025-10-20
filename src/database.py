#!/usr/bin/env python3
"""
Database handler for storing paper metadata
Uses SQLite for structured storage with JSON export capabilities
"""
import sqlite3
import json
import threading
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path

from .models import PaperMetadata, CollectionStats
from .config import DATABASE_PATH


class PaperDatabase:
    """SQLite database handler for paper metadata"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        """Initialize database connection and create tables if needed"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30.0)
        self.conn.row_factory = sqlite3.Row
        # Add thread lock for database operations
        self._lock = threading.Lock()
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        with self._lock:
            cursor = self.conn.cursor()
            
            # Queries table (must be created first due to foreign key)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_text TEXT NOT NULL,
                    description TEXT,
                    created_date TEXT NOT NULL
                )
            """)
            
            # Papers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    pmid TEXT PRIMARY KEY,
                    pmcid TEXT,
                    doi TEXT,
                    title TEXT,
                    abstract TEXT,
                    full_text TEXT,
                    full_text_sections TEXT,
                    mesh_terms TEXT,
                    keywords TEXT,
                    authors TEXT,
                    year TEXT,
                    date_published TEXT,
                    journal TEXT,
                    is_full_text_pmc INTEGER,
                    oa_url TEXT,
                    primary_topic TEXT,
                    topic_name TEXT,
                    topic_subfield TEXT,
                    topic_field TEXT,
                    topic_domain TEXT,
                    citation_normalized_percentile REAL,
                    cited_by_count INTEGER,
                    fwci REAL,
                    collection_date TEXT,
                    openalex_retrieved INTEGER,
                    parsing_status TEXT,
                    query_id INTEGER,
                    embedding BLOB,
                    YAKE_keywords TEXT,
                    source TEXT DEFAULT 'PubMed'
                )
            """)
            
            # Migration: Add source column to existing databases
            try:
                cursor.execute("SELECT source FROM papers LIMIT 1")
            except:
                # Column doesn't exist, add it and set all existing papers to PubMed
                print("🔄 Migrating database: Adding 'source' column...")
                cursor.execute("ALTER TABLE papers ADD COLUMN source TEXT DEFAULT 'PubMed'")
                cursor.execute("UPDATE papers SET source = 'PubMed' WHERE source IS NULL")
                self.conn.commit()
                print("✓ Migration complete: All existing papers marked as 'PubMed'")
            
            
            # Collection runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS collection_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT,
                    total_found INTEGER,
                    total_processed INTEGER,
                    with_full_text INTEGER,
                    without_full_text INTEGER,
                    with_openalex INTEGER,
                    failed_pubmed INTEGER,
                    failed_openalex INTEGER,
                    start_time TEXT,
                    end_time TEXT
                )
            """)
            
            # Failed DOIs table (for papers without PMC full text)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS failed_dois (
                    doi TEXT PRIMARY KEY,
                    pmid TEXT,
                    reason TEXT,
                    timestamp TEXT
                )
            """)
            
            self.conn.commit()
    
    def insert_paper(self, metadata: PaperMetadata) -> bool:
        """
        Insert or update a paper in the database.
        
        Args:
            metadata: PaperMetadata object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._lock:
                cursor = self.conn.cursor()
                # Use explicit column names for schema flexibility
                # This way, adding new columns won't break existing code
                cursor.execute("""
                    INSERT OR REPLACE INTO papers (
                        pmid, pmcid, doi, title, abstract, full_text, full_text_sections,
                        mesh_terms, keywords, authors, year, date_published, journal,
                        is_full_text_pmc, oa_url, primary_topic, topic_name, topic_subfield,
                        topic_field, topic_domain, citation_normalized_percentile,
                        cited_by_count, fwci, collection_date, openalex_retrieved,
                        parsing_status, query_id, embedding, YAKE_keywords, source
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    metadata.pmid,
                    metadata.pmcid,
                    metadata.doi,
                    metadata.title,
                    metadata.abstract,
                    metadata.full_text,
                    json.dumps(metadata.full_text_sections) if metadata.full_text_sections else None,
                    json.dumps(metadata.mesh_terms),
                    json.dumps(metadata.keywords),
                    json.dumps(metadata.authors),
                    metadata.year,
                    metadata.date_published,
                    metadata.journal,
                    1 if metadata.is_full_text_pmc else 0,
                    metadata.oa_url,
                    json.dumps(metadata.primary_topic) if metadata.primary_topic else None,
                    # Extract individual topic fields
                    metadata.primary_topic.get('display_name') if metadata.primary_topic else None,
                    metadata.primary_topic.get('subfield', {}).get('display_name') if metadata.primary_topic and 'subfield' in metadata.primary_topic else None,
                    metadata.primary_topic.get('field', {}).get('display_name') if metadata.primary_topic and 'field' in metadata.primary_topic else None,
                    metadata.primary_topic.get('domain', {}).get('display_name') if metadata.primary_topic and 'domain' in metadata.primary_topic else None,
                    metadata.citation_normalized_percentile,
                    metadata.cited_by_count,
                    metadata.fwci,
                    metadata.collection_date,
                    1 if metadata.openalex_retrieved else 0,
                    getattr(metadata, 'parsing_status', None),  # May not exist on old metadata
                    metadata.query_id,
                    getattr(metadata, 'embedding', None),  # BLOB, may not exist on old metadata
                    getattr(metadata, 'YAKE_keywords', None),  # May not exist on old metadata
                    getattr(metadata, 'source', 'PubMed')  # Source field
                ))
                self.conn.commit()
            return True
        except Exception as e:
            print(f"Error inserting paper {metadata.pmid}: {str(e)}")
            return False
    
    def insert_papers_batch(self, metadata_list: List[PaperMetadata]) -> int:
        """
        Insert multiple papers in a batch.
        
        Args:
            metadata_list: List of PaperMetadata objects
            
        Returns:
            Number of successfully inserted papers
        """
        success_count = 0
        for metadata in metadata_list:
            if self.insert_paper(metadata):
                success_count += 1
        return success_count
    
    def paper_exists(self, pmid: str) -> bool:
        """
        Check if a paper exists in the database by PMID.
        
        Args:
            pmid: PubMed ID
            
        Returns:
            True if paper exists, False otherwise
        """
        if not pmid:
            return False
            
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1 FROM papers WHERE pmid = ? LIMIT 1", (pmid,))
            return cursor.fetchone() is not None
    
    def paper_exists_by_doi(self, doi: str) -> bool:
        """
        Check if a paper exists in the database by DOI.
        
        Args:
            doi: DOI of the paper
            
        Returns:
            True if paper exists, False otherwise
        """
        if not doi:
            return False
        
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1 FROM papers WHERE doi = ? LIMIT 1", (doi,))
            return cursor.fetchone() is not None
    
    def paper_needs_enrichment(self, identifier: str) -> tuple[bool, Optional[PaperMetadata]]:
        """
        Check if a paper needs enrichment (missing abstract or full text).
        
        Args:
            identifier: PMID or DOI
            
        Returns:
            Tuple of (needs_enrichment, metadata)
            - needs_enrichment: True if paper exists but is missing abstract or full text
            - metadata: PaperMetadata object if paper exists, None otherwise
        """
        # Try to get paper by PMID first, then by DOI
        paper = self.get_paper(identifier)
        if not paper and identifier:
            paper = self.get_paper_by_doi(identifier)
        
        if not paper:
            return (False, None)  # Paper doesn't exist
        
        # Check if paper needs enrichment
        needs_enrichment = (
            not paper.abstract or 
            not paper.full_text or
            paper.abstract.strip() == "" or
            paper.full_text is None
        )
        
        return (needs_enrichment, paper)
    
    def get_paper(self, pmid: str) -> Optional[PaperMetadata]:
        """
        Retrieve a paper by PMID.
        
        Args:
            pmid: PubMed ID
            
        Returns:
            PaperMetadata object or None if not found
        """
        if not pmid:
            return None
            
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM papers WHERE pmid = ?", (pmid,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_metadata(row)
            return None
    
    def get_paper_by_doi(self, doi: str) -> Optional[PaperMetadata]:
        """
        Retrieve a paper by DOI.
        
        Args:
            doi: DOI of the paper
            
        Returns:
            PaperMetadata object or None if not found
        """
        if not doi:
            return None
        
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM papers WHERE doi = ?", (doi,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_metadata(row)
            return None
    
    def get_papers_without_fulltext(self) -> List[PaperMetadata]:
        """Get all papers that don't have full text from PMC"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE is_full_text_pmc = 0")
        rows = cursor.fetchall()
        return [self._row_to_metadata(row) for row in rows]
    
    def get_papers_with_fulltext(self) -> List[PaperMetadata]:
        """Get all papers that have full text from PMC"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE is_full_text_pmc = 1")
        rows = cursor.fetchall()
        return [self._row_to_metadata(row) for row in rows]
    
    def get_all_papers(self) -> List[PaperMetadata]:
        """Get all papers from database"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM papers")
        rows = cursor.fetchall()
        return [self._row_to_metadata(row) for row in rows]
    
    def add_failed_doi(self, doi: str, pmid: str, reason: str, timestamp: str):
        """Add a DOI to the failed list"""
        try:
            with self._lock:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO failed_dois VALUES (?, ?, ?, ?)
                """, (doi, pmid, reason, timestamp))
                self.conn.commit()
        except Exception as e:
            print(f"Error adding failed DOI {doi}: {str(e)}")
    
    def get_failed_dois(self) -> List[Dict]:
        """Get all failed DOIs"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM failed_dois")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def save_collection_stats(self, stats: CollectionStats) -> int:
        """
        Save collection run statistics.
        
        Args:
            stats: CollectionStats object
            
        Returns:
            ID of the inserted row
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO collection_runs VALUES (
                NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            stats.query,
            stats.total_found,
            stats.total_processed,
            stats.with_full_text,
            stats.without_full_text,
            stats.with_openalex,
            stats.failed_pubmed,
            stats.failed_openalex,
            stats.start_time,
            stats.end_time
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def export_to_json(self, output_path: str = None, compact: bool = True) -> str:
        """
        Export all papers to JSON file.
        
        Args:
            output_path: Path to output JSON file
            compact: If True, use compact JSON (no indentation, 50-70% smaller and faster)
            
        Returns:
            Path to the exported file
        """
        if output_path is None:
            # Derive data directory from database path instead of using imported DATA_DIR
            db_dir = Path(self.db_path).parent
            output_path = db_dir / "papers_export.json"
        
        print(f"Exporting papers to JSON (this may take a while for large datasets)...")
        papers = self.get_all_papers()
        papers_dict = [paper.to_dict() for paper in papers]
        
        # Use compact format by default (no indentation) for speed and size
        # With 50k papers: compact=~1GB, indent=2.4GB (2.4x larger!)
        with open(output_path, 'w', encoding='utf-8') as f:
            if compact:
                json.dump(papers_dict, f, ensure_ascii=False, separators=(',', ':'))
            else:
                json.dump(papers_dict, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Exported {len(papers)} papers to {output_path}")
        return str(output_path)
    
    def export_failed_dois_to_file(self, output_path: str = None, format: str = 'json') -> str:
        """
        Export failed DOIs to a structured file.
        
        Args:
            output_path: Path to output file
            format: Output format ('json' or 'txt')
            
        Returns:
            Path to the exported file
        """
        papers = self.get_papers_without_fulltext()
        
        if format == 'json':
            if output_path is None:
                # Derive data directory from database path instead of using imported DATA_DIR
                db_dir = Path(self.db_path).parent
                output_path = db_dir / "failed_dois.json"
            
            failed_papers = []
            for paper in papers:
                # Extract topic information
                topic_info = {}
                if paper.primary_topic:
                    topic_info = {
                        'topic_name': paper.primary_topic.get('display_name'),
                        'topic_subfield': paper.primary_topic.get('subfield', {}).get('display_name') if 'subfield' in paper.primary_topic else None,
                        'topic_field': paper.primary_topic.get('field', {}).get('display_name') if 'field' in paper.primary_topic else None,
                        'topic_domain': paper.primary_topic.get('domain', {}).get('display_name') if 'domain' in paper.primary_topic else None
                    }
                
                failed_papers.append({
                    'pmid': paper.pmid,
                    'doi': paper.doi,
                    'title': paper.title,
                    'journal': paper.journal,
                    'year': paper.year,
                    'authors': paper.authors[:3] if paper.authors else [],  # First 3 authors
                    'abstract': paper.abstract[:200] + '...' if paper.abstract and len(paper.abstract) > 200 else paper.abstract,
                    'oa_url': paper.oa_url,
                    'primary_topic': paper.primary_topic,  # Full dictionary for backward compatibility
                    'topic_info': topic_info,  # Structured topic information
                    'collection_date': paper.collection_date
                })
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'total_count': len(failed_papers),
                    'papers': failed_papers
                }, f, indent=2, ensure_ascii=False)
        
        else:  # txt format
            if output_path is None:
                # Derive data directory from database path instead of using imported DATA_DIR
                db_dir = Path(self.db_path).parent
                output_path = db_dir / "failed_dois.txt"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("# Papers without PMC full text\n")
                f.write("# Format: DOI | PMID | Title\n\n")
                for paper in papers:
                    doi = paper.doi if paper.doi else "NO_DOI"
                    title = paper.title[:80] if paper.title else "NO_TITLE"
                    f.write(f"{doi} | {paper.pmid} | {title}\n")
        
        print(f"Exported {len(papers)} papers without full text to {output_path}")
        return str(output_path)
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        cursor = self.conn.cursor()
        
        stats = {}
        cursor.execute("SELECT COUNT(*) FROM papers")
        stats['total_papers'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM papers WHERE is_full_text_pmc = 1")
        stats['with_fulltext'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM papers WHERE is_full_text_pmc = 0")
        stats['without_fulltext'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM papers WHERE openalex_retrieved = 1")
        stats['with_openalex'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM failed_dois")
        stats['failed_dois'] = cursor.fetchone()[0]
        
        return stats
    
    def _row_to_metadata(self, row: sqlite3.Row) -> PaperMetadata:
        """Convert database row to PaperMetadata object"""
        # Load primary_topic from JSON if available, otherwise construct from individual fields
        primary_topic = None
        if row['primary_topic']:
            primary_topic = json.loads(row['primary_topic'])
        elif row['topic_name']:
            # Construct a simplified primary_topic dict from individual fields
            primary_topic = {
                'display_name': row['topic_name']
            }
            
            # Add subfield if available
            if row['topic_subfield']:
                primary_topic['subfield'] = {
                    'display_name': row['topic_subfield']
                }
                
            # Add field if available
            if row['topic_field']:
                primary_topic['field'] = {
                    'display_name': row['topic_field']
                }
                
            # Add domain if available
            if row['topic_domain']:
                primary_topic['domain'] = {
                    'display_name': row['topic_domain']
                }
        
        return PaperMetadata(
            pmid=row['pmid'],
            pmcid=row['pmcid'],
            doi=row['doi'],
            title=row['title'],
            abstract=row['abstract'],
            full_text=row['full_text'],
            full_text_sections=json.loads(row['full_text_sections']) if row['full_text_sections'] else {},
            mesh_terms=json.loads(row['mesh_terms']) if row['mesh_terms'] else [],
            keywords=json.loads(row['keywords']) if row['keywords'] else [],
            authors=json.loads(row['authors']) if row['authors'] else [],
            year=row['year'],
            date_published=row['date_published'],
            journal=row['journal'],
            is_full_text_pmc=bool(row['is_full_text_pmc']),
            oa_url=row['oa_url'],
            primary_topic=primary_topic,
            citation_normalized_percentile=row['citation_normalized_percentile'],
            cited_by_count=row['cited_by_count'],
            fwci=row['fwci'],
            collection_date=row['collection_date'],
            openalex_retrieved=bool(row['openalex_retrieved']),
            query_id=row['query_id'] if 'query_id' in row.keys() else None,
            source=row['source'] if 'source' in row.keys() else 'PubMed'
        )
    
    def insert_query(self, query_text: str, description: str = None) -> int:
        """
        Insert a new query into the queries table.
        
        Args:
            query_text: The PubMed query text
            description: Optional description of the query
            
        Returns:
            The ID of the inserted query
        """
        from datetime import datetime
        with self._lock:
            cursor = self.conn.cursor()
            created_date = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO queries (query_text, description, created_date)
                VALUES (?, ?, ?)
            """, (query_text, description, created_date))
            self.conn.commit()
            return cursor.lastrowid
    
    def get_query(self, query_id: int) -> Optional[Dict]:
        """
        Get a query by ID.
        
        Args:
            query_id: Query ID
            
        Returns:
            Dictionary with query details or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM queries WHERE id = ?", (query_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def get_all_queries(self) -> List[Dict]:
        """Get all queries from the database"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM queries ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]
    
    def get_papers_by_query(self, query_id: int) -> List[PaperMetadata]:
        """
        Get all papers collected with a specific query.
        
        Args:
            query_id: Query ID
            
        Returns:
            List of PaperMetadata objects
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE query_id = ?", (query_id,))
        return [self._row_to_metadata(row) for row in cursor.fetchall()]
    
    def count_papers_by_query(self, query_id: int) -> int:
        """
        Count papers collected with a specific query.
        
        Args:
            query_id: Query ID
            
        Returns:
            Number of papers
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM papers WHERE query_id = ?", (query_id,))
        return cursor.fetchone()[0]
    
    def close(self):
        """Close database connection"""
        self.conn.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
