#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Clean previous builds
echo "Cleaning old builds..."
rm -rf build dist *.egg-info

# Build the source distribution and wheel distribution using uv
echo "Building package with uv..."
uv build

echo "Build complete. Distribution packages are in the 'dist' directory."
