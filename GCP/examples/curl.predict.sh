#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"

curl -sS -X POST "${BASE_URL}/v1/predict" \
  -H "Content-Type: application/json" \
  --data @"$(dirname "$0")/request.predict.json"
