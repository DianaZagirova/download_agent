#!/usr/bin/env python3
"""
Utilities for text conversion and manipulation
"""
from typing import Dict, Optional, List, Tuple


def sections_to_flat_text(sections: Dict[str, str]) -> str:
    """
    Convert a dictionary of sections to flat text.
    
    Args:
        sections: Dictionary mapping section names to content
        
    Returns:
        Flat text with section headers
    """
    if not sections:
        return ""
    
    # Sort sections by name to ensure consistent ordering
    # Special sections like 'Abstract', 'Introduction' should come first
    priority_sections = ['Abstract', 'Introduction', 'Main', 'Methods', 'Results', 'Discussion', 'Conclusion']
    
    # Create a list of (priority, section_name) tuples for sorting
    section_order = []
    for name in sections.keys():
        try:
            # Find the position in priority list, or use a large number if not found
            priority = priority_sections.index(name)
        except ValueError:
            priority = 100  # Not in priority list
            
        section_order.append((priority, name))
    
    # Sort by priority
    section_order.sort()
    
    # Build the flat text
    parts = []
    for _, section_name in section_order:
        content = sections[section_name].strip()
        if not content:
            continue
            
        # Add section header (except for 'Main')
        if section_name.lower() != 'main':
            parts.append(f"## {section_name}\n\n")
            
        # Add content
        parts.append(f"{content}\n\n")
    
    return "".join(parts).strip()


def flat_text_to_sections(text: str) -> Dict[str, str]:
    """
    Convert flat text with markdown headers to a dictionary of sections.
    
    Args:
        text: Flat text with markdown headers
        
    Returns:
        Dictionary mapping section names to content
    """
    if not text:
        return {}
    
    sections = {}
    current_section = "Main"
    current_content = []
    
    # Split text into lines
    lines = text.split('\n')
    
    for line in lines:
        # Check if line is a section header (## Section Name)
        if line.startswith('## '):
            # Save previous section
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()
                current_content = []
            
            # Extract new section name
            current_section = line.lstrip('#').strip()
        else:
            current_content.append(line)
    
    # Save the last section
    if current_content:
        sections[current_section] = '\n'.join(current_content).strip()
    
    return sections


def extract_section(sections: Dict[str, str], section_name: str) -> Optional[str]:
    """
    Extract a specific section from the sections dictionary.
    
    Args:
        sections: Dictionary mapping section names to content
        section_name: Name of the section to extract
        
    Returns:
        Section content or None if not found
    """
    # Try exact match
    if section_name in sections:
        return sections[section_name]
    
    # Try case-insensitive match
    section_name_lower = section_name.lower()
    for name, content in sections.items():
        if name.lower() == section_name_lower:
            return content
    
    # Try partial match
    for name, content in sections.items():
        if section_name_lower in name.lower():
            return content
    
    return None


def get_section_names(sections: Dict[str, str]) -> List[str]:
    """
    Get a list of section names.
    
    Args:
        sections: Dictionary mapping section names to content
        
    Returns:
        List of section names
    """
    return list(sections.keys())


def merge_sections(sections1: Dict[str, str], sections2: Dict[str, str]) -> Dict[str, str]:
    """
    Merge two section dictionaries.
    
    Args:
        sections1: First dictionary of sections
        sections2: Second dictionary of sections
        
    Returns:
        Merged dictionary
    """
    merged = sections1.copy()
    
    for name, content in sections2.items():
        if name in merged:
            # Append content to existing section
            merged[name] = f"{merged[name]}\n\n{content}"
        else:
            # Add new section
            merged[name] = content
    
    return merged


def find_section_by_keywords(sections: Dict[str, str], keywords: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Find a section that contains specific keywords.
    
    Args:
        sections: Dictionary mapping section names to content
        keywords: List of keywords to search for
        
    Returns:
        Tuple of (section_name, section_content) or (None, None) if not found
    """
    for name, content in sections.items():
        for keyword in keywords:
            if keyword.lower() in content.lower():
                return name, content
    
    return None, None
