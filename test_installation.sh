#!/bin/bash
# Comprehensive installation test for fibermorph across Python versions

set -e

COLORS_RED='\033[0;31m'
COLORS_GREEN='\033[0;32m'
COLORS_YELLOW='\033[1;33m'
COLORS_NC='\033[0m' # No Color

echo "==================================================================="
echo "  Fibermorph Installation Test Suite"
echo "==================================================================="
echo ""

# Function to test a specific Python version
test_python_version() {
    local python_cmd=$1
    local version_name=$2
    local test_dir="/tmp/fibermorph-test-${version_name}"
    
    echo "-------------------------------------------------------------------"
    echo "Testing with $version_name"
    echo "-------------------------------------------------------------------"
    
    if ! command -v $python_cmd &> /dev/null; then
        echo -e "${COLORS_YELLOW}⚠ ${version_name} not found, skipping${COLORS_NC}"
        echo ""
        return
    fi
    
    local py_version=$($python_cmd --version 2>&1)
    echo "✓ Found: $py_version"
    
    # Create fresh venv
    rm -rf "$test_dir"
    $python_cmd -m venv "$test_dir"
    source "$test_dir/bin/activate"
    
    # Upgrade pip quietly
    pip install --upgrade pip -q
    
    # Install fibermorph
    echo "  Installing fibermorph..."
    pip install fibermorph -q
    
    # Check what was installed
    local installed_version=$(pip show fibermorph | grep "Version:" | awk '{print $2}')
    local numpy_version=$(pip show numpy | grep "Version:" | awk '{print $2}')
    local has_pyarrow=$(pip show pyarrow 2>/dev/null | grep "Version:" | awk '{print $2}')
    
    echo "  ├─ fibermorph: $installed_version"
    echo "  ├─ numpy: $numpy_version"
    if [ -n "$has_pyarrow" ]; then
        echo "  └─ pyarrow: $has_pyarrow"
    else
        echo "  └─ pyarrow: (not installed)"
    fi
    
    # Test imports
    echo "  Testing imports..."
    if python -c "
import fibermorph
import numpy
import pandas
import matplotlib
import scipy
import sklearn
import skimage
print('  ✓ All imports successful')
" 2>/dev/null; then
        echo -e "${COLORS_GREEN}✓ $version_name: PASSED${COLORS_NC}"
    else
        echo -e "${COLORS_RED}✗ $version_name: FAILED (import error)${COLORS_NC}"
    fi
    
    # Test CLI
    if fibermorph --help > /dev/null 2>&1; then
        echo "  ✓ CLI working"
    else
        echo "  ✗ CLI failed"
    fi
    
    # Cleanup
    deactivate
    rm -rf "$test_dir"
    echo ""
}

# Test all available Python versions
test_python_version "python3.9" "Python 3.9"
test_python_version "python3.10" "Python 3.10"
test_python_version "python3.11" "Python 3.11"
test_python_version "python3.12" "Python 3.12"
test_python_version "python3.13" "Python 3.13"

echo "==================================================================="
echo "  Test Suite Complete"
echo "==================================================================="
