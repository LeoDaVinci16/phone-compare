#!/usr/bin/env bash
# Update the website copy of the report (docs/index.html). Run "conda activate phone-compare" first.
set -e
cd "$(dirname "$0")"
phone-compare --no-plots "$@"
mkdir -p docs && cp output/report.html docs/index.html && touch docs/.nojekyll
echo 'Website updated: docs/index.html. Publish: git add docs && git commit -m "Update website" && git push'
