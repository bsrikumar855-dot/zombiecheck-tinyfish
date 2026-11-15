#!/usr/bin/env bash
# One-command demo on a real list: the free-for-dev "awesome" list (1,300+ dev tools and services).
# usage: TINYFISH_API_KEY=... ./demo.sh [rows]     (default 600)
set -euo pipefail
cd "$(dirname "$0")"
: "${TINYFISH_API_KEY:?set TINYFISH_API_KEY}"
N="${1:-600}"
mkdir -p demo
[ -s demo/free-for-dev.csv ] || python3 awesome_to_csv.py https://raw.githubusercontent.com/ripienaar/free-for-dev/master/README.md > demo/free-for-dev.csv
python3 zombiecheck.py demo/free-for-dev.csv -o demo/free-for-dev.checked.csv --limit "$N"
echo "Open demo/free-for-dev.checked.report.html, or import demo/free-for-dev.checked.xlsx into Google Sheets."
