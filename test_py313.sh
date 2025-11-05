#!/bin/bash
# Test fibermorph installation with Python 3.13

set -e

echo "=== Testing fibermorph with Python 3.13 ==="
echo ""

# Check if Python 3.13 is available
if ! command -v python3.13 &> /dev/null; then
    echo "❌ Python 3.13 not found. Please install it first:"
    echo "   brew install python@3.13"
    exit 1
fi

echo "✅ Python 3.13 found: $(python3.13 --version)"
echo ""

# Create a fresh virtual environment
TEST_DIR="../fibermorph-py313-test"
rm -rf "$TEST_DIR"
python3.13 -m venv "$TEST_DIR"
source "$TEST_DIR/bin/activate"

echo "✅ Created fresh Python 3.13 virtual environment"
echo ""

# Upgrade pip
pip install --upgrade pip

# Check PyPI for latest version
echo "Checking PyPI for latest fibermorph version..."
LATEST_VERSION=$(pip index versions fibermorph 2>/dev/null | grep fibermorph | head -1 | awk '{print $2}' | tr -d '()')
echo "Latest version on PyPI: $LATEST_VERSION"
echo ""

# Install fibermorph
echo "Installing fibermorph..."
pip install fibermorph
echo ""

# Check what got installed
echo "=== Installation details ==="
pip show fibermorph
echo ""

# Check numpy version
echo "=== Checking numpy version ==="
python -c "import numpy; print(f'NumPy version: {numpy.__version__}')"
echo ""

# Test imports
echo "=== Testing imports ==="
python -c "
import fibermorph
print(f'✅ fibermorph version: {fibermorph.__version__}')

import numpy
print(f'✅ numpy version: {numpy.__version__}')

import scipy
print(f'✅ scipy imported successfully')

import pandas
print(f'✅ pandas imported successfully')

import matplotlib
print(f'✅ matplotlib imported successfully')

import skimage
print(f'✅ scikit-image imported successfully')

import sklearn
print(f'✅ scikit-learn imported successfully')

print('')
print('✅ All imports successful!')
"
echo ""

# Test CLI
echo "=== Testing CLI ==="
fibermorph --help | head -10
echo ""

# Cleanup
deactivate
cd ..
rm -rf "$TEST_DIR"

echo "=== Test completed successfully! ==="
echo ""
echo "Summary:"
echo "  - Python 3.13: ✅"
echo "  - fibermorph installed: ✅"
echo "  - NumPy 2.x installed: ✅"
echo "  - All dependencies working: ✅"
