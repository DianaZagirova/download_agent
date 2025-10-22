import os
import sys
import time
import requests
import csv
import sys
from pathlib import Path
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
        
# Import your paper_names list
from data.dois_validation.dois_validation import paper_names

def get_doi_from_title(title):
    """Query the CrossRef API for a DOI using the title."""
    url = 'https://api.crossref.org/works'
    params = {
        'query.bibliographic': title,
        'rows': 1
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data['message']['items']
        if items:
            return items[0].get('DOI', None)
        return None
    except Exception as e:
        print(f"Error with title '{title}': {e}")
        return None

results = []

for title in paper_names:
    print(f"Querying: {title[:80]}...")
    doi = get_doi_from_title(title)
    results.append((title, doi))
    print(f" -> DOI: {doi}")
    time.sleep(1)  # Be polite to the API.

# Save as a txt file (tab-separated)
output_file = "data/dois_validation/dois_validation_2.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    for title, doi in results:
        f.write(f"{title}:{doi}\n")

# Save as a txt file (tab-separated)
output_file = "data/dois_validation/dois_validation_2_only_DOIS.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    for title, doi in results:
        f.write(f"{doi}\n")

print(f"\nDONE! Results saved as '{output_file}'.")