#!/bin/bash
# scripts/build_layer.sh

set -e  # Exit on error

echo "=== Building Lambda Layer ==="

# Clean previous builds
rm -rf lambda_layer dist/dependencies_layer.zip

# Create layer directory with proper Python structure
mkdir -p lambda_layer/python

echo "Installing dependencies from requirements.txt..."

# Install packages to the layer directory
pip install \
    --platform manylinux2014_x86_64 \
    --target lambda_layer/python \
    --python-version 3.12 \
    --implementation cp \
    --only-binary=:all: \
    --upgrade \
    -r requirements.txt

echo "Cleaning up unnecessary files..."

# Remove cache and other unnecessary files
find lambda_layer -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find lambda_layer -type f -name "*.pyc" -delete
find lambda_layer -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find lambda_layer -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true

echo "Creating ZIP file..."

# Create the ZIP (must be at lambda_layer root, not inside python/)
cd lambda_layer
zip -r ../dist/dependencies_layer.zip python/

echo "=== Layer Build Complete ==="
echo "Layer size: $(du -sh lambda_layer)"
echo "ZIP size: $(du -h ../dist/dependencies_layer.zip)"