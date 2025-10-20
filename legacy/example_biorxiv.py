#!/usr/bin/env python3
"""
Example script for downloading bioRxiv papers
"""

from download_biorxiv import collect_biorxiv_papers


def example_aging_papers():
    """Download papers about aging from bioRxiv"""
    collect_biorxiv_papers(
        query="aging senescence longevity",
        max_results=500,
        use_threading=True,
        output_dir="biorxiv_aging_papers",
        query_description="bioRxiv papers about aging and senescence",
        server="biorxiv"
    )


def example_covid_papers():
    """Download COVID-19 papers from medRxiv"""
    collect_biorxiv_papers(
        query="covid-19 sars-cov-2",
        max_results=1000,
        use_threading=True,
        output_dir="medrxiv_covid_papers",
        query_description="medRxiv papers about COVID-19",
        server="medrxiv"
    )


def example_neuroscience_papers():
    """Download neuroscience papers from bioRxiv"""
    collect_biorxiv_papers(
        query="neuroscience brain plasticity",
        max_results=300,
        use_threading=True,
        output_dir="biorxiv_neuroscience",
        query_description="bioRxiv neuroscience papers",
        server="biorxiv"
    )


if __name__ == "__main__":
    # Run one of the examples
    print("Select an example:")
    print("1. Aging papers from bioRxiv")
    print("2. COVID-19 papers from medRxiv")
    print("3. Neuroscience papers from bioRxiv")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        example_aging_papers()
    elif choice == "2":
        example_covid_papers()
    elif choice == "3":
        example_neuroscience_papers()
    else:
        print("Invalid choice. Running aging papers example...")
        example_aging_papers()
