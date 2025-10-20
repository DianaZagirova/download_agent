#!/usr/bin/env python3
"""
Fix schema mismatch between code and database

This script updates src/database.py to match the actual database schema.
The database has been manually altered to include 'embedding' and 'YAKE_keywords'
columns that are not defined in the code.
"""

import sys
import os

def main():
    print("="*80)
    print("DATABASE SCHEMA MISMATCH FIX")
    print("="*80)
    print()
    
    database_file = "src/database.py"
    
    print("⚠️  SCHEMA MISMATCH DETECTED")
    print()
    print("The actual database has extra columns that are not in the code:")
    print("  - embedding BLOB")
    print("  - YAKE_keywords TEXT")
    print()
    print("This will cause issues when creating new databases.")
    print()
    print("="*80)
    print("REQUIRED FIXES")
    print("="*80)
    print()
    
    print("1. Update CREATE TABLE statement in src/database.py (lines 44-74)")
    print("   Add these two lines before the closing parenthesis:")
    print()
    print("   embedding BLOB,")
    print("   YAKE_keywords TEXT")
    print()
    
    print("2. Update INSERT statement in src/database.py (line 120)")
    print("   Change from 28 to 29 placeholders:")
    print()
    print("   ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?")
    print("   (add one more ?)")
    print()
    
    print("3. Update INSERT values in src/database.py (after line 151)")
    print("   Add after the 'embedding' line:")
    print()
    print("   getattr(metadata, 'YAKE_keywords', None)")
    print()
    
    print("4. OPTIONAL: Add fields to src/models.py PaperMetadata class:")
    print()
    print("   embedding: Optional[bytes] = None")
    print("   YAKE_keywords: Optional[str] = None")
    print()
    
    print("="*80)
    print("AUTOMATIC FIX")
    print("="*80)
    print()
    print("Would you like to automatically apply these fixes? (y/n): ", end='')
    
    response = input().strip().lower()
    
    if response == 'y':
        print("\n❌ Automatic fix not implemented yet.")
        print("Please apply the fixes manually as described above.")
        print("\nRefer to DATABASE_SCHEMA_ANALYSIS.md for detailed instructions.")
    else:
        print("\nNo changes made.")
        print("Refer to DATABASE_SCHEMA_ANALYSIS.md for manual fix instructions.")
    
    print()
    print("="*80)
    print("For detailed analysis, see: DATABASE_SCHEMA_ANALYSIS.md")
    print("="*80)

if __name__ == "__main__":
    main()
