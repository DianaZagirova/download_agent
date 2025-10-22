#!/bin/bash

# AI-Powered Aging Research Collection System - Setup Script
# This script sets up a reproducible environment for the project

set -e  # Exit on any error

echo "🧬 AI-Powered Aging Research Collection System - Setup"
echo "======================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3.8+ is available
check_python() {
    print_status "Checking Python version..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
            print_success "Python $PYTHON_VERSION found (✓ 3.8+ required)"
            PYTHON_CMD="python3"
        else
            print_error "Python 3.8+ required, found $PYTHON_VERSION"
            exit 1
        fi
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
            print_success "Python $PYTHON_VERSION found (✓ 3.8+ required)"
            PYTHON_CMD="python"
        else
            print_error "Python 3.8+ required, found $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python not found. Please install Python 3.8 or higher."
        exit 1
    fi
}

# Create virtual environment
create_venv() {
    print_status "Creating virtual environment..."
    
    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists. Removing old one..."
        rm -rf venv
    fi
    
    $PYTHON_CMD -m venv venv
    print_success "Virtual environment created"
}

# Activate virtual environment and install dependencies
install_dependencies() {
    print_status "Activating virtual environment and installing dependencies..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    print_status "Upgrading pip..."
    pip install --upgrade pip
    
    # Install requirements
    print_status "Installing project dependencies..."
    pip install -r requirements.txt
    
    print_success "All dependencies installed successfully"
}

# Create necessary directories
create_directories() {
    print_status "Creating project directories..."
    
    mkdir -p paper_collection/{data,logs,cache,checkpoints}
    mkdir -p paper_collection_test/{data,logs,cache,checkpoints}
    mkdir -p documentation
    
    print_success "Project directories created"
}

# Run demonstration
run_demo() {
    print_status "Running demonstration..."
    echo ""
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Run the demo
    python demo.py
    
    if [ $? -eq 0 ]; then
        print_success "Demonstration completed successfully!"
    else
        print_warning "Demonstration had issues, but setup is complete"
    fi
}

# Main setup function
main() {
    echo "This script will set up a reproducible environment for the"
    echo "AI-Powered Aging Research Collection System."
    echo ""
    echo "What this script does:"
    echo "• Checks Python 3.8+ availability"
    echo "• Creates a virtual environment"
    echo "• Installs all required dependencies"
    echo "• Creates necessary project directories"
    echo "• Runs a demonstration"
    echo ""
    
    read -p "Continue? (y/N): " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 0
    fi
    
    echo ""
    print_status "Starting setup process..."
    echo ""
    
    # Run setup steps
    check_python
    create_venv
    install_dependencies
    create_directories
    
    echo ""
    print_success "Setup completed successfully!"
    echo ""
    echo "To use the system:"
    echo "1. Activate the virtual environment: source venv/bin/activate"
    echo "2. Run the demonstration: python demo.py"
    echo "3. Or run the main collection script: python scripts/run_full.py --help"
    echo ""
    
    # Ask if user wants to run demo
    read -p "Run demonstration now? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        run_demo
    fi
    
    echo ""
    print_success "Setup complete! Happy researching! 🧬"
}

# Run main function
main "$@"
