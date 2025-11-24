rm -rf dist
uv build
twine upload dist/*
uv publish

