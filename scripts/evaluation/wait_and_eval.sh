#!/bin/bash
# Wait for dataset_v2.jsonl to appear, clear cache, then run evaluation
DATASET="data/eval/dataset_v2.jsonl"
RESULTS="data/eval/results_v2.jsonl"
API_URL="http://localhost:8010"
LLM_URL="http://localhost:8011/v1"

echo "Waiting for $DATASET..."
while [ ! -f "$DATASET" ]; do
    sleep 10
done

echo "Dataset ready: $(wc -l < $DATASET) lines"
echo "Clearing Redis cache..."
curl -s -X POST "$API_URL/api/cache/clear" && echo ""

echo "Starting evaluation..."
.venv/bin/python scripts/evaluation/evaluate.py \
    --dataset "$DATASET" \
    --api-url "$API_URL" \
    --llm-url "$LLM_URL" \
    --concurrency 2 \
    --results-jsonl "$RESULTS"

echo "Done! Compare:"
echo "  .venv/bin/python scripts/evaluation/evaluate.py --compare data/eval/results_v1.jsonl $RESULTS"
