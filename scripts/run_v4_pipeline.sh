#!/bin/bash
# Full v4 pipeline: contextual enrichment → hybrid reindex → evaluation
# Run after vLLM is healthy and chatbot backend is up.
set -e

API_URL="http://localhost:8010"
LLM_URL="http://localhost:8011/v1"
RESULTS="data/eval/results_v4.jsonl"

echo "=== Step 1: Generate contextual enrichment cache ==="
.venv/bin/python scripts/ingestion/contextual_enrichment.py \
    --data-dir data/raw \
    --llm-url "$LLM_URL" \
    --cache data/enrichment_cache.jsonl

echo ""
echo "=== Step 2: Wipe Qdrant and hybrid reindex ==="
.venv/bin/python scripts/ingestion/ingest_courses.py \
    --all \
    --wipe \
    --hybrid \
    --data-dir data/raw \
    --enrichment-cache data/enrichment_cache.jsonl \
    --bm25-vocab data/bm25_vocab.json

echo ""
echo "=== Step 3: Restart chatbot backend to pick up new BM25 vocab ==="
docker restart fcim-chatbot-backend
echo "Waiting 30s for backend to start..."
sleep 30
until curl -sf "$API_URL/health" > /dev/null 2>&1; do sleep 3; done
echo "Backend healthy"

echo ""
echo "=== Step 4: Clear cache ==="
curl -s -X POST "$API_URL/api/cache/clear"
echo ""

echo ""
echo "=== Step 5: Evaluation v4 ==="
.venv/bin/python scripts/evaluation/evaluate.py \
    --dataset data/eval/dataset_v2.jsonl \
    --api-url "$API_URL" \
    --llm-url "$LLM_URL" \
    --concurrency 2 \
    --results-jsonl "$RESULTS"

echo ""
echo "=== Step 6: Compare all versions ==="
.venv/bin/python scripts/evaluation/evaluate.py \
    --compare data/eval/results_v1.jsonl data/eval/results_v2.jsonl
echo ""
.venv/bin/python scripts/evaluation/evaluate.py \
    --compare data/eval/results_v2.jsonl "$RESULTS"
