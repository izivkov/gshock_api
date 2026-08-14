#!/bin/bash
set -e

# Extract current version from pyproject.toml
VERSION=$(grep -E '^version\s*=' pyproject.toml | head -1 | sed 's/.*= *"\(.*\)"/\1/')
echo "Preparing to upload gshock-api v${VERSION} to PyPI"
echo ""
read -p "Continue? [y/N] " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "Aborted."
    exit 1
fi

# Clean previous builds
rm -rf dist

# Build distributions with uv
uv build

# Upload distributions using twine within uv environment
uv run twine upload dist/*

echo ""
echo "Successfully uploaded gshock-api v${VERSION} to PyPI."
