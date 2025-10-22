#!/usr/bin/env python3
"""
Demonstration script for the AI-Powered Aging Theories Research Collection System
This script showcases the system's capabilities with a small, manageable dataset.
"""

import os
import sys
import subprocess
from datetime import datetime

def print_banner():
    """Print a professional banner for the demonstration"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🧬 AI-Powered Aging Research Collection                   ║
║                              Demonstration Script                            ║
║                                                                              ║
║  This script demonstrates the sophisticated capabilities of our system:     ║
║  • AI-driven query generation and optimization                              ║
║  • Multi-source data integration (PubMed, OpenAlex, PMC)                   ║
║  • High-performance parallel processing                                     ║
║  • Advanced error handling and recovery                                     ║
║  • Comprehensive data validation and quality assurance                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_environment():
    """Check if the environment is properly set up"""
    print("🔍 Checking environment setup...")
    
    # Check if virtual environment is activated
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment detected")
    else:
        print("⚠️  Warning: No virtual environment detected. Consider using a venv for reproducibility.")
    
    # Check if required packages are installed
    try:
        import requests
        import tqdm
        import sqlite3
        print("✅ Required packages available")
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False
    
    return True

def run_demonstration():
    """Run the main demonstration"""
    print("\n🚀 Starting demonstration...")
    print("="*80)
    
    # Define demonstration queries
    demo_queries = [
        "(\"theory of aging\"[Title]) AND (\"Aging\"[Mesh]) AND (2020:2025[dp]) AND (full text[sb])",
        "(\"aging\"[tiab] AND \"theory\"[tiab])",
        "(\"senescence\"[tiab] AND \"mechanism\"[tiab])"
    ]
    
    # Create timestamp for this run
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_name = f"demo_run_{timestamp}"
    
    print(f"📊 Demonstration Configuration:")
    print(f"   • Queries: {len(demo_queries)} diverse aging research queries")
    print(f"   • Query 1: Recent aging theories (2020-2025, full text)")
    print(f"   • Query 2: General aging and theory papers")
    print(f"   • Query 3: Senescence mechanism studies")
    print(f"   • Max Results: 50 papers per query (150 total)")
    print(f"   • Test Database: Enabled (separate from main data)")
    print(f"   • Run Name: {run_name}")
    print(f"   • Output: paper_collection_test/")
    print()
    
    # Build the command
    cmd = [
        "python", "scripts/run_full.py",
        "--queries"] + demo_queries + [
        "--query-run-name", run_name,
        "--max-results", "50",
        "--test-db",
        "--use-suffix",
        "--queries-suffix", "AND (Aging[MeSH] OR Geriatrics[MeSH]) NOT (cosmetic*[tiab] OR dermatol*[tiab])"
    ]
    
    print("🔧 Executing collection command...")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        # Run the collection
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        # Check if collection was successful (look for success indicators in output)
        if "Collection completed successfully!" in result.stdout or "Database statistics:" in result.stdout:
            print("✅ Collection completed successfully!")
            print("\n📈 Results Summary:")
            
            # Parse and display key results from output
            lines = result.stdout.split('\n')
            for line in lines:
                if "Total papers found:" in line or "Papers with full text:" in line or "Database:" in line or "total_papers:" in line:
                    print(f"   {line.strip()}")
            
            print(f"\n📁 Output Location:")
            print(f"   • Database: paper_collection_test/data/test_papers.db")
            print(f"   • JSON Export: paper_collection_test/data/test_papers_export.json")
            print(f"   • Logs: paper_collection_test/logs/")
            
        else:
            print("❌ Collection encountered errors:")
            print("STDOUT:", result.stdout[-1000:])  # Show last 1000 chars
            print("STDERR:", result.stderr[-500:])   # Show last 500 chars
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Collection timed out (5 minutes). This is normal for larger datasets.")
        print("The system is designed to handle much larger collections efficiently.")
        return False
    except Exception as e:
        print(f"❌ Error running demonstration: {e}")
        return False
    
    return True

def show_advanced_features():
    """Display information about advanced features"""
    print("\n🔬 Advanced Features Demonstrated:")
    print("="*50)
    
    features = [
        "🤖 AI-Driven Query Optimization",
        "🔄 Multi-Source Data Integration (PubMed + OpenAlex + PMC)",
        "⚡ High-Performance Parallel Processing",
        "🛡️  Robust Error Handling & Recovery",
        "📊 Comprehensive Data Validation",
        "💾 Efficient SQLite Storage with JSON Export",
        "🔍 Intelligent Caching & Rate Limiting",
        "📝 Detailed Logging & Monitoring",
        "🧪 Test Database Isolation",
        "🔧 Configurable Processing Parameters"
    ]
    
    for feature in features:
        print(f"   {feature}")
    
    print(f"\n📚 Query Intelligence:")
    print(f"   • 40+ specific aging theories covered")
    print(f"   • Evolutionary, molecular, and systems approaches")
    print(f"   • Intelligent exclusion filters")
    print(f"   • Dynamic query refinement based on result volume")

def show_usage_examples():
    """Show additional usage examples"""
    print("\n💡 Additional Usage Examples:")
    print("="*40)
    
    examples = [
        {
            "title": "Comprehensive Aging Theories Collection",
            "command": "python scripts/run_full.py --queries \"(\"aging\"[tiab] AND theory[tiab])\" --query-run-name \"theories_study\" --max-results 10000"
        },
        {
            "title": "Hallmarks of Aging Research",
            "command": "python scripts/run_full.py --queries \"(\"hallmarks of aging\"[tiab])\" --query-run-name \"hallmarks_study\" --max-results 5000"
        },
        {
            "title": "Intervention Studies",
            "command": "python scripts/run_full.py --queries \"(\"calorie restriction\"[tiab] AND aging[tiab])\" --query-run-name \"interventions\" --max-results 3000"
        },
        {
            "title": "Custom Output Directory",
            "command": "python scripts/run_full.py --queries \"(\"senescence\"[tiab])\" --query-run-name \"custom_study\" --output-dir /path/to/output"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['title']}:")
        print(f"   {example['command']}")

def main():
    """Main demonstration function"""
    print_banner()
    
    # Check environment
    if not check_environment():
        print("\n❌ Environment check failed. Please fix the issues above and try again.")
        return 1
    
    print("\n" + "="*80)
    
    # Run demonstration
    success = run_demonstration()
    
    if success:
        show_advanced_features()
        show_usage_examples()
        
        print("\n🎉 Demonstration completed successfully!")
        print("\nThis system is designed to handle much larger collections (50,000+ papers)")
        print("with the same level of sophistication and reliability.")
        print("\nFor production use, consider:")
        print("• Running with higher max-results values")
        print("• Using the main database (remove --test-db flag)")
        print("• Configuring custom output directories")
        print("• Setting up monitoring and alerting")
        
        return 0
    else:
        print("\n❌ Demonstration failed. Please check the error messages above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
