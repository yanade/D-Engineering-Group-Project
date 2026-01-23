#!/bin/bash
# scripts/build_layer.sh

set -e  # Exit on error
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== Building Lambda Layer ==="

# Clean previous builds
rm -rf "${ROOT_DIR}/lambda_layer" "${ROOT_DIR}/dist/dependencies_layer.zip"

# Create layer directory with proper Python structure
mkdir -p "${ROOT_DIR}/lambda_layer/python"

echo "Installing dependencies from requirements-layer..."

# Install packages to the layer directory
python -m pip install \
    --platform manylinux2014_x86_64 \
    --target "${ROOT_DIR}/lambda_layer/python" \
    --python-version 3.11 \
    --implementation cp \
    --only-binary=:all: \
    --upgrade \
    -r requirements-layer.txt

echo "Cleaning up unnecessary files..."

# Remove cache and other unnecessary files
echo "Cleaning up unnecessary files..."

find "${ROOT_DIR}/lambda_layer" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${ROOT_DIR}/lambda_layer" -type f -name "*.pyc" -delete
find "${ROOT_DIR}/lambda_layer" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true



echo "Creating ZIP file..."

# Create the ZIP (must be at lambda_layer root, not inside python/)
mkdir -p "${ROOT_DIR}/dist"
cd "${ROOT_DIR}/lambda_layer"
zip -r "${ROOT_DIR}/dist/dependencies_layer.zip" python/

echo "=== Layer Build Complete ==="
echo "Layer size: $(du -sh "${ROOT_DIR}/lambda_layer")"
echo "ZIP size: $(du -h "${ROOT_DIR}/dist/dependencies_layer.zip")"