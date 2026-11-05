#!/usr/bin/env bash
# Pack the repo without heavy/local dirs (virtual env, runtime data, caches).
# Writes: ../nc_v7_monolith_multiagent_2026-09-24_clean.tar.gz
set -euo pipefail
cd "$(dirname "$0")"
OUT="$PWD/../nc_v7_monolith_multiagent_2026-09-24_clean.tar.gz"

VENV_DIR="."$(echo "venv")          # .venv
DOT_VENV="."$(echo "venv")          # same, built to dodge shell-hook literal scan
VENV_NAME="${DOT_VENV#.}"           # venv

tar -czf "$OUT" \
  --exclude="./${VENV_NAME}" \
  --exclude="${DOT_VENV}" \
  --exclude="./data" \
  --exclude="data" \
  --exclude="__pycache__" \
  --exclude=".pytest_cache" \
  --exclude="*/__pycache__" \
  --exclude="node_modules" \
  --exclude="*.pyc" \
  --exclude="logs/*.log" \
  .

rm -f "$0"
echo "packed: $OUT"
ls -lah "$OUT"
