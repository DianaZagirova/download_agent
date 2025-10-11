#!/usr/bin/env python3
"""
Text cleaning utilities for full text processing
"""
import re


def clean_full_text(text: str) -> str:
    """
    Clean full text by removing LaTeX commands, special characters, and formatting artifacts.
    
    Args:
        text: Raw full text string
        
    Returns:
        Cleaned text string
    """
    if not text:
        return text
    
    # Remove complete LaTeX blocks (documentclass + packages + content)
    # Pattern: \documentclass....\begin{document}...\end{document}
    text = re.sub(
        r'\\documentclass\[.*?\]\{.*?\}.*?\\begin\{document\}(.*?)\\end\{document\}',
        r'\1',  # Keep only the content between begin/end document
        text,
        flags=re.DOTALL
    )
    
    # Remove standalone LaTeX document class declarations
    text = re.sub(r'\\documentclass\[.*?\]\{.*?\}', '', text)
    
    # Remove LaTeX usepackage commands
    text = re.sub(r'\\usepackage\{.*?\}', '', text)
    
    # Remove LaTeX setlength commands
    text = re.sub(r'\\setlength\{.*?\}\{.*?\}', '', text)
    
    # Remove LaTeX begin/end document tags
    text = re.sub(r'\\begin\{document\}', '', text)
    text = re.sub(r'\\end\{document\}', '', text)
    
    # Replace common LaTeX math symbols with readable text
    replacements = {
        r'\$\$\\alpha\$\$': 'α',
        r'\$\$\\beta\$\$': 'β',
        r'\$\$\\gamma\$\$': 'γ',
        r'\$\$\\delta\$\$': 'δ',
        r'\\alpha': 'α',
        r'\\beta': 'β',
        r'\\gamma': 'γ',
        r'\\delta': 'δ',
        r'\\mu': 'μ',
        r'\\sigma': 'σ',
        r'\\lambda': 'λ',
        r'\\theta': 'θ',
        r'\\pi': 'π',
        r'\\omega': 'ω',
    }
    
    for latex, symbol in replacements.items():
        text = re.sub(latex, symbol, text)
    
    # Remove other LaTeX commands but keep content in braces
    text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)
    
    # Remove remaining backslash commands
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    
    # Clean up dollar signs (LaTeX math mode)
    text = re.sub(r'\$+', '', text)
    
    # Remove excessive tabs and spaces
    text = re.sub(r'\t+', ' ', text)
    text = re.sub(r' {3,}', ' ', text)
    
    # Remove multiple newlines (keep max 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # Remove lines that are just special characters or very short (but keep meaningful short lines)
    lines = [line for line in text.split('\n') 
             if len(line.strip()) > 1 and not re.match(r'^[\W_]+$', line.strip())]
    text = '\n'.join(lines)
    
    return text.strip()


def clean_abstract(text: str) -> str:
    """
    Clean abstract text (lighter cleaning than full text).
    
    Args:
        text: Raw abstract string
        
    Returns:
        Cleaned abstract string
    """
    if not text:
        return text
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters at start/end
    text = text.strip()
    
    return text


def remove_references_section(text: str) -> str:
    """
    Remove the references section from full text to reduce noise.
    
    Args:
        text: Full text string
        
    Returns:
        Text without references section
    """
    if not text:
        return text
    
    # Try to find common reference section markers
    patterns = [
        r'\n##\s*REFERENCES\s*\n.*',
        r'\nREFERENCES\s*\n.*',
        r'\n##\s*References\s*\n.*',
        r'\nReferences\s*\n.*',
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
    
    return text


def clean_text_comprehensive(text: str, remove_references: bool = True) -> str:
    """
    Comprehensive text cleaning pipeline.
    
    Args:
        text: Raw text string
        remove_references: Whether to remove references section
        
    Returns:
        Fully cleaned text
    """
    if not text:
        return text
    
    # Apply all cleaning steps
    text = clean_full_text(text)
    
    if remove_references:
        text = remove_references_section(text)
    
    return text


def clean_sections(sections: dict) -> dict:
    """
    Clean a dictionary of text sections.
    
    Args:
        sections: Dictionary mapping section names to content
        
    Returns:
        Dictionary with cleaned sections
    """
    if not sections:
        return {}
    
    cleaned_sections = {}
    
    for section_name, content in sections.items():
        # Skip empty sections
        if not content or not content.strip():
            continue
            
        # Clean section content
        # Don't remove references from individual sections unless it's the References section
        remove_refs = section_name.lower() in ['references', 'bibliography', 'literature cited']
        cleaned_content = clean_text_comprehensive(content, remove_references=remove_refs)
        
        # Only add non-empty sections
        if cleaned_content and cleaned_content.strip():
            cleaned_sections[section_name] = cleaned_content
    
    return cleaned_sections


def preview_cleaning(text: str, max_length: int = 500) -> tuple[str, str]:
    """
    Preview the effect of cleaning on text.
    
    Args:
        text: Raw text string
        max_length: Maximum length to show in preview
        
    Returns:
        Tuple of (original_preview, cleaned_preview)
    """
    original = text[:max_length] + "..." if len(text) > max_length else text
    cleaned = clean_text_comprehensive(text)
    cleaned_preview = cleaned[:max_length] + "..." if len(cleaned) > max_length else cleaned
    
    return original, cleaned_preview


if __name__ == "__main__":
    # Test the cleaning function
    test_text = """
    The Gompertz parameters differ across sexes and across countries. On average across countries, women face a lower \\documentclass[12pt]{minimal}
    \\usepackage{amsmath}
    \\usepackage{wasysym} 
    \\usepackage{amsfonts} 
    \\usepackage{amssymb} 
    \\usepackage{amsbsy}
    \\usepackage{mathrsfs}
    \\usepackage{upgreek}
    \\setlength{\\oddsidemargin}{-69pt}
    \\begin{document}$$\\alpha$$\\end{document} and a higher \\documentclass[12pt]{minimal}
    \\begin{document}$$\\beta$$\\end{document}
    """
    
    print("Original text:")
    print(test_text)
    print("\n" + "="*60 + "\n")
    print("Cleaned text:")
    print(clean_text_comprehensive(test_text))
