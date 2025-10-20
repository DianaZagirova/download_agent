#!/usr/bin/env python3
"""
Data models for paper metadata
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from datetime import datetime
import json


@dataclass
class PaperMetadata:
    """Complete metadata for a scientific paper"""
    
    # PubMed fields
    pmid: str
    pmcid: Optional[str] = None
    doi: Optional[str] = None
    title: Optional[str] = None
    abstract: Optional[str] = None
    full_text: Optional[str] = None  # Full text without abstract (flat format)
    full_text_sections: Optional[Dict[str, str]] = field(default_factory=dict)  # Structured full text by sections
    mesh_terms: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    authors: List[str] = field(default_factory=list)
    year: Optional[str] = None
    date_published: Optional[str] = None
    journal: Optional[str] = None
    is_full_text_pmc: bool = False
    
    # OpenAlex fields
    oa_url: Optional[str] = None
    primary_topic: Optional[Dict] = None
    citation_normalized_percentile: Optional[float] = None
    cited_by_count: Optional[int] = None
    fwci: Optional[float] = None
    
    # System fields
    collection_date: str = field(default_factory=lambda: datetime.now().isoformat())
    openalex_retrieved: bool = False
    query_id: Optional[int] = None  # Reference to the query used to collect this paper
    source: str = "PubMed"  # Source: "PubMed", "EuropePMC", "BioRxiv", etc.
    
    # Properties for topic fields
    @property
    def topic_name(self) -> Optional[str]:
        """Get the topic name from primary_topic"""
        if self.primary_topic and isinstance(self.primary_topic, dict):
            return self.primary_topic.get('display_name')
        return None
    
    @property
    def topic_subfield(self) -> Optional[str]:
        """Get the topic subfield name from primary_topic"""
        if self.primary_topic and isinstance(self.primary_topic, dict) and 'subfield' in self.primary_topic:
            return self.primary_topic['subfield'].get('display_name')
        return None
    
    @property
    def topic_field(self) -> Optional[str]:
        """Get the topic field name from primary_topic"""
        if self.primary_topic and isinstance(self.primary_topic, dict) and 'field' in self.primary_topic:
            return self.primary_topic['field'].get('display_name')
        return None
    
    @property
    def topic_domain(self) -> Optional[str]:
        """Get the topic domain name from primary_topic"""
        if self.primary_topic and isinstance(self.primary_topic, dict) and 'domain' in self.primary_topic:
            return self.primary_topic['domain'].get('display_name')
        return None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PaperMetadata':
        """Create instance from dictionary"""
        return cls(**data)
    
    def has_full_text(self) -> bool:
        """Check if paper has full text available"""
        has_flat_text = bool(self.full_text and len(self.full_text.strip()) > 0)
        has_sectioned_text = bool(self.full_text_sections and len(self.full_text_sections) > 0)
        return has_flat_text or has_sectioned_text
        
    def get_full_text(self, format: str = 'auto') -> Optional[str]:
        """Get full text in the requested format
        
        Args:
            format: 'flat', 'sectioned', or 'auto' (prefers sectioned if available)
            
        Returns:
            Full text string or None if not available
        """
        if format == 'flat' or (format == 'auto' and not self.full_text_sections):
            return self.full_text
        
        elif format == 'sectioned' or (format == 'auto' and self.full_text_sections):
            if not self.full_text_sections:
                return None
            
            # Convert sections to formatted text
            text_parts = []
            for section_name, section_content in self.full_text_sections.items():
                # Skip empty sections
                if not section_content or not section_content.strip():
                    continue
                
                # Format section header
                if section_name.lower() != 'main':
                    text_parts.append(f"## {section_name}\n")
                
                # Add content
                text_parts.append(f"{section_content.strip()}\n\n")
            
            return '\n'.join(text_parts).strip()
        
        return None
        
    def get_sections(self) -> List[str]:
        """Get list of available section names"""
        if self.full_text_sections:
            return list(self.full_text_sections.keys())
        return []
    
    def get_summary(self) -> str:
        """Get a brief summary of the paper"""
        return f"PMID: {self.pmid} | DOI: {self.doi} | Title: {self.title[:50]}..."


@dataclass
class CollectionStats:
    """Statistics for a collection run"""
    query: str
    total_found: int = 0
    total_processed: int = 0
    with_full_text: int = 0
    without_full_text: int = 0
    with_openalex: int = 0
    failed_pubmed: int = 0
    failed_openalex: int = 0
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    def print_summary(self):
        """Print collection statistics"""
        print("\n" + "="*60)
        print("COLLECTION STATISTICS")
        print("="*60)
        print(f"Query: {self.query[:100]}...")
        print(f"Total papers found: {self.total_found}")
        print(f"Total papers processed: {self.total_processed}")
        print(f"Papers with full text from PMC: {self.with_full_text}")
        print(f"Papers without full text: {self.without_full_text}")
        print(f"Papers with OpenAlex data: {self.with_openalex}")
        print(f"Failed PubMed retrievals: {self.failed_pubmed}")
        print(f"Failed OpenAlex retrievals: {self.failed_openalex}")
        if self.end_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            duration = (end - start).total_seconds()
            print(f"Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        print("="*60 + "\n")
