#!/usr/bin/env python3
"""
Test content validation to ensure we correctly identify meaningful full text
vs boilerplate/metadata sections
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pubmed_extractor import has_meaningful_content

# Test cases
test_cases = [
    {
        "name": "Real full text article",
        "sections": {
            "Abstract": "This is the abstract...",
            "Introduction": "Lorem ipsum " * 100,  # 1300 chars
            "Methods": "We conducted experiments " * 80,  # 2000 chars
            "Results": "Our findings show " * 90,  # 1620 chars
            "Discussion": "These results indicate " * 70,  # 1610 chars
            "Acknowledgments": "We thank the funding agency"
        },
        "full_text": "Abstract + Introduction + Methods + Results + Discussion",
        "expected": True,
        "reason": "Has multiple meaningful sections (Introduction, Methods, Results, Discussion)"
    },
    {
        "name": "Only boilerplate",
        "sections": {
            "Abstract": "This is the abstract...",
            "Conflict of Interest": "The authors declare no conflicts",
            "Acknowledgments": "We thank everyone",
            "Funding": "This work was funded by..."
        },
        "full_text": "Short text with only metadata",
        "expected": False,
        "reason": "Only boilerplate sections, no meaningful content"
    },
    {
        "name": "Abstract + one small section",
        "sections": {
            "Abstract": "This is the abstract...",
            "Conflict of Interest": "No conflicts"
        },
        "full_text": "Abstract text plus conflict statement",
        "expected": False,
        "reason": "Only one small boilerplate section beyond abstract"
    },
    {
        "name": "Multiple substantial sections without clear names",
        "sections": {
            "Abstract": "This is the abstract...",
            "Section 1": "Lorem ipsum " * 100,  # 1300 chars
            "Section 2": "Dolor sit amet " * 100,  # 1500 chars
            "Section 3": "Consectetur adipiscing " * 100,  # 2200 chars
        },
        "full_text": "Long text with multiple sections",
        "expected": True,
        "reason": "Has 3 substantial sections (>500 chars each)"
    },
    {
        "name": "One meaningful section",
        "sections": {
            "Abstract": "This is the abstract...",
            "Introduction": "Lorem ipsum " * 100,  # 1300 chars
            "Acknowledgments": "Thanks"
        },
        "full_text": "Abstract + Introduction + Acknowledgments",
        "expected": True,
        "reason": "Has at least one meaningful section (Introduction)"
    },
    {
        "name": "Short sections only",
        "sections": {
            "Abstract": "This is the abstract...",
            "Note": "Short note",
            "Comment": "Brief comment",
            "Acknowledgments": "Thanks"
        },
        "full_text": "All sections are very short",
        "expected": False,
        "reason": "No substantial sections (all < 500 chars)"
    },
    {
        "name": "Very long text without sections",
        "sections": {},
        "full_text": "Lorem ipsum dolor sit amet " * 200,  # 5400 chars
        "expected": True,
        "reason": "No sections but text is > 2000 chars"
    },
    {
        "name": "Short text without sections",
        "sections": {},
        "full_text": "Short text",
        "expected": False,
        "reason": "No sections and text is < 2000 chars"
    }
]

print("="*70)
print("CONTENT VALIDATION TESTS")
print("="*70)

passed = 0
failed = 0

for test in test_cases:
    result = has_meaningful_content(test["sections"], test["full_text"])
    expected = test["expected"]
    status = "✓ PASS" if result == expected else "✗ FAIL"
    
    if result == expected:
        passed += 1
    else:
        failed += 1
    
    print(f"\n{status}: {test['name']}")
    print(f"  Expected: {expected}, Got: {result}")
    print(f"  Reason: {test['reason']}")
    if result != expected:
        print(f"  Sections: {list(test['sections'].keys())}")
        print(f"  Full text length: {len(test['full_text'])} chars")

print(f"\n{'='*70}")
print(f"RESULTS: {passed} passed, {failed} failed")
print("="*70)

if failed > 0:
    sys.exit(1)
