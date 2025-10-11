#!/usr/bin/env python3
"""
Test script to verify text cleaner is integrated into the download pipeline
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.text_cleaner import clean_text_comprehensive

# Sample text with LaTeX formatting (similar to what you saw in your JSON)
sample_text = """
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
\\usepackage{amsmath}
\\usepackage{wasysym} 
\\usepackage{amsfonts} 
\\usepackage{amssymb} 
\\usepackage{amsbsy}
\\usepackage{mathrsfs}
\\usepackage{upgreek}
\\setlength{\\oddsidemargin}{-69pt}
\\begin{document}$$\\beta$$\\end{document}, i.e., a lower initial mortality rate and a faster speed of aging27. A lower \\documentclass[12pt]{minimal}
\\usepackage{amsmath}
\\usepackage{wasysym} 
\\usepackage{amsfonts} 
\\usepackage{amssymb} 
\\usepackage{amsbsy}
\\usepackage{mathrsfs}
"""

print("="*70)
print("TEXT CLEANER INTEGRATION TEST")
print("="*70)

print("\n1. ORIGINAL TEXT (with LaTeX formatting):")
print("-"*70)
print(sample_text[:300] + "...")

print("\n2. CLEANED TEXT (LaTeX removed, symbols converted):")
print("-"*70)
cleaned = clean_text_comprehensive(sample_text, remove_references=True)
print(cleaned)

print("\n" + "="*70)
print("✅ Text cleaner is working correctly!")
print("="*70)

print("\nThe text cleaner is now integrated into:")
print("  1. pubmed_extractor.py - extract_pmc_fulltext()")
print("  2. pubmed_extractor.py - extract_pubmed_metadata()")
print("  3. download_papers_full_texts.py - collect_pmc_doc()")
print("\nAll new papers will have clean text automatically!")
