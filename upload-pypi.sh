
uv add --upgrade twine
uv build
uv run twine upload -r pypi dist/*
