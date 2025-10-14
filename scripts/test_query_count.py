#!/usr/bin/env python3
"""
Test script to verify the PubMed query count
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Bio import Entrez
from src.config import ENTREZ_EMAIL, ENTREZ_API_KEY

# Query to test
query = """(
  ("aging"[tiab] OR "ageing"[tiab] OR "senescence"[tiab] OR "longevity"[tiab]) AND
  (theory[tiab] OR theories[tiab] OR hypothes*[tiab] OR framework*[tiab] OR paradigm*[tiab] OR "ultimate cause"[tiab] OR "proximate cause"[tiab] OR "evolution*"[tiab])
  NOT (cosmetic*[tiab] OR sunscreen*[tiab] OR "facial"[tiab] OR dermatol*[tiab])
  NOT ("healthy aging"[tiab] OR wellbeing[tiab] OR "public health"[tiab])
  NOT ("religion"[tiab])
  NOT ("Cosmetics"[mh])
  NOT ("Skin"[mh] OR "Dermatology"[mh])
)"""

print("Testing PubMed query count...")
print(f"Query: {query}")
print("\n" + "="*70)

Entrez.email = ENTREZ_EMAIL
Entrez.api_key = ENTREZ_API_KEY

try:
    # Use retmax=0 to just get the count
    handle = Entrez.esearch(db="pubmed", term=query, retmax=0)
    record = Entrez.read(handle)
    handle.close()
    
    count = int(record["Count"])
    print(f"✓ Query returned: {count:,} results")
    
    expected_count = 46351
    if count == expected_count:
        print(f"✅ SUCCESS: Count matches expected {expected_count:,} results")
    else:
        print(f"⚠️  WARNING: Count is {count:,}, expected {expected_count:,}")
        print(f"   Difference: {count - expected_count:+,}")
    
    print("="*70)
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)
