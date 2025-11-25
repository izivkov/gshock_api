#!/bin/bash
set -e

# Clean previous builds
rm -rf dist

# Build distributions with uv
uv build

# Upload distributions using twine within uv environment
uv run twine upload dist/*
