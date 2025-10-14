#!/usr/bin/env python3
"""
Utility to view and manage collection logs
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Get logs directory
log_dir = Path(__file__).parent.parent / 'paper_collection' / 'logs'

def list_logs():
    """List all available log files"""
    if not log_dir.exists():
        print(f"Logs directory not found: {log_dir}")
        return
    
    log_files = sorted(log_dir.glob('collection_run_*.log'), reverse=True)
    error_files = sorted(log_dir.glob('collection_errors_*.log'), reverse=True)
    
    if not log_files:
        print("No log files found.")
        return
    
    print("\n" + "="*80)
    print("AVAILABLE LOG FILES")
    print("="*80)
    
    print("\nCollection Logs:")
    for i, log_file in enumerate(log_files, 1):
        size = log_file.stat().st_size
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        print(f"{i}. {log_file.name}")
        print(f"   Size: {size:,} bytes ({size/1024:.1f} KB)")
        print(f"   Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if error_files:
        print("\nError Logs:")
        for i, log_file in enumerate(error_files, 1):
            size = log_file.stat().st_size
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            print(f"{i}. {log_file.name}")
            print(f"   Size: {size:,} bytes ({size/1024:.1f} KB)")
            print(f"   Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

def view_latest(lines=50):
    """View the last N lines of the most recent log"""
    log_files = sorted(log_dir.glob('collection_run_*.log'), reverse=True)
    
    if not log_files:
        print("No log files found.")
        return
    
    latest = log_files[0]
    print(f"\nViewing last {lines} lines of: {latest.name}")
    print("="*80)
    
    with open(latest, 'r') as f:
        all_lines = f.readlines()
        for line in all_lines[-lines:]:
            print(line, end='')

def view_log(log_name, lines=None):
    """View a specific log file"""
    log_path = log_dir / log_name
    
    if not log_path.exists():
        print(f"Log file not found: {log_name}")
        return
    
    print(f"\nViewing: {log_name}")
    print("="*80)
    
    with open(log_path, 'r') as f:
        if lines:
            all_lines = f.readlines()
            for line in all_lines[-lines:]:
                print(line, end='')
        else:
            print(f.read())

def tail_log(log_name=None):
    """Tail (follow) a log file in real-time"""
    if log_name:
        log_path = log_dir / log_name
    else:
        log_files = sorted(log_dir.glob('collection_run_*.log'), reverse=True)
        if not log_files:
            print("No log files found.")
            return
        log_path = log_files[0]
    
    if not log_path.exists():
        print(f"Log file not found: {log_path}")
        return
    
    print(f"\nTailing: {log_path.name}")
    print("Press Ctrl+C to stop")
    print("="*80)
    
    try:
        with open(log_path, 'r') as f:
            # Go to end
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    print(line, end='')
                else:
                    import time
                    time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopped tailing.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/view_logs.py [command] [options]")
        print("\nCommands:")
        print("  list              - List all available log files")
        print("  latest [N]        - View last N lines of latest log (default: 50)")
        print("  view <file> [N]   - View specific log file (optionally last N lines)")
        print("  tail [file]       - Follow log file in real-time (default: latest)")
        print("\nExamples:")
        print("  python scripts/view_logs.py list")
        print("  python scripts/view_logs.py latest 100")
        print("  python scripts/view_logs.py view collection_run_20251013_151234.log")
        print("  python scripts/view_logs.py tail")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_logs()
    
    elif command == "latest":
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        view_latest(lines)
    
    elif command == "view":
        if len(sys.argv) < 3:
            print("Error: Please specify log file name")
            print("Usage: python scripts/view_logs.py view <filename> [lines]")
            sys.exit(1)
        log_name = sys.argv[2]
        lines = int(sys.argv[3]) if len(sys.argv) > 3 else None
        view_log(log_name, lines)
    
    elif command == "tail":
        log_name = sys.argv[2] if len(sys.argv) > 2 else None
        tail_log(log_name)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
