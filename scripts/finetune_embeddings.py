#!/usr/bin/env python3
"""
Fine-tune multilingual-e5-large on domain-specific QA pairs.

Uses MultipleNegativesRankingLoss (MNRL) — the standard approach for
embedding fine-tuning. Each (question, passage) pair trains the model
to rank the correct passage higher than all other in-batch passages.

After training: update EMBEDDINGS_MODEL in .env and re-ingest Qdrant.

Usage:
    # Stop vLLM first to free GPU memory, then:
    python scripts/finetune_embeddings.py \
        --dataset data/eval/dataset_v2.jsonl \
        --output models/e5-finetuned \
        --device cuda

    # CPU (slower, ~60-90 min, vLLM can keep running):
    python scripts/finetune_embeddings.py \
        --dataset data/eval/dataset_v2.jsonl \
        --output models/e5-finetuned \
        --device cpu
"""

import argparse
import json
import random
import sys
from pathlib import Path

# Sentence-transformers imports
from sentence_transformers import SentenceTransformer, InputExample, losses
from sentence_transformers.evaluation import InformationRetrievalEvaluator
from sentence_transformers.training_args import SentenceTransformerTrainingArguments
from torch.utils.data import DataLoader

BASE_MODEL = "intfloat/multilingual-e5-large"
SEED = 42


def load_pairs(dataset_path: str) -> list[dict]:
    pairs = []
    seen_chunks = set()
    skipped_dups = 0

    with open(dataset_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            q = rec.get("question", "").strip()
            p = rec.get("chunk_text", "").strip()
            if not q or not p:
                continue
            # Deduplicate by chunk_text — same chunk appearing twice would
            # create false negatives in MNRL (both positives in same batch).
            if p in seen_chunks:
                skipped_dups += 1
                continue
            seen_chunks.add(p)
            pairs.append({"question": q, "passage": p})

    print(f"Loaded {len(pairs)} unique pairs ({skipped_dups} duplicate chunks skipped)")
    return pairs


def build_evaluator(eval_pairs: list[dict]) -> InformationRetrievalEvaluator:
    queries = {str(i): p["question"] for i, p in enumerate(eval_pairs)}
    corpus  = {str(i): p["passage"]  for i, p in enumerate(eval_pairs)}
    relevant = {str(i): {str(i)} for i in range(len(eval_pairs))}

    return InformationRetrievalEvaluator(
        queries=queries,
        corpus=corpus,
        relevant_docs=relevant,
        show_progress_bar=False,
        precision_recall_at_k=[1, 3, 5],
        name="eval",
    )


def main():
    parser = argparse.ArgumentParser(description="Fine-tune embedding model on QA pairs")
    parser.add_argument("--dataset",    default="data/eval/dataset_v2.jsonl")
    parser.add_argument("--base-model", default=BASE_MODEL)
    parser.add_argument("--output",     default="models/e5-finetuned")
    parser.add_argument("--device",     default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--epochs",     type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr",         type=float, default=2e-5)
    parser.add_argument("--bf16",       action="store_true", default=True,
                        help="Use bf16 mixed precision (default: True on CUDA)")
    parser.add_argument("--eval-split", type=float, default=0.15,
                        help="Fraction held out for evaluation")
    args = parser.parse_args()

    random.seed(SEED)
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. Load data
    # -------------------------------------------------------------------------
    all_pairs = load_pairs(args.dataset)
    random.shuffle(all_pairs)

    n_eval  = max(50, int(len(all_pairs) * args.eval_split))
    n_train = len(all_pairs) - n_eval
    train_pairs = all_pairs[:n_train]
    eval_pairs  = all_pairs[n_train:]
    print(f"Train: {n_train}  |  Eval: {n_eval}")

    # -------------------------------------------------------------------------
    # 2. Load base model
    # -------------------------------------------------------------------------
    print(f"\nLoading {args.base_model} on {args.device}...")
    model = SentenceTransformer(args.base_model, device=args.device)

    # -------------------------------------------------------------------------
    # 3. Build training examples — E5 prefix convention
    # -------------------------------------------------------------------------
    train_examples = [
        InputExample(texts=[f"query: {p['question']}", f"passage: {p['passage']}"])
        for p in train_pairs
    ]

    train_dataloader = DataLoader(
        train_examples,
        shuffle=True,
        batch_size=args.batch_size,
    )

    # MNRL: treats every other sample in the batch as a negative
    train_loss = losses.MultipleNegativesRankingLoss(model)

    # -------------------------------------------------------------------------
    # 4. Evaluator (recall@5 on held-out pairs)
    # -------------------------------------------------------------------------
    evaluator = build_evaluator(eval_pairs)

    # -------------------------------------------------------------------------
    # 5. Train
    # -------------------------------------------------------------------------
    steps_per_epoch = len(train_dataloader)
    total_steps     = steps_per_epoch * args.epochs
    warmup_steps    = max(1, int(total_steps * 0.1))
    use_bf16        = args.bf16 and args.device == "cuda"

    print(f"\nTraining for {args.epochs} epochs  ({total_steps} steps, {warmup_steps} warmup)")
    print(f"Batch size: {args.batch_size}  |  LR: {args.lr}  |  bf16: {use_bf16}\n")

    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        evaluator=evaluator,
        epochs=args.epochs,
        warmup_steps=warmup_steps,
        optimizer_params={"lr": args.lr},
        output_path=str(output_path),
        save_best_model=True,
        show_progress_bar=True,
        use_amp=use_bf16,
    )

    print(f"\nBest model saved to: {output_path}")
    print("\nNext steps:")
    print("  1. Update .env:  EMBEDDINGS_MODEL=" + str(output_path.absolute()))
    print("  2. Reindex Qdrant: python scripts/ingestion/ingest_courses.py --all --wipe")
    print("  3. Restart docker: docker restart fcim-chatbot-backend")


if __name__ == "__main__":
    main()
