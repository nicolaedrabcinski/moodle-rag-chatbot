#!/usr/bin/env python3
"""
Generate document-level context summaries for Contextual Chunk Enrichment.

For each source file, calls the LLM to produce a 2-3 sentence summary
describing what the document is about. These summaries are prepended to
every chunk from that document before embedding, giving the embedding model
richer context than the raw chunk alone.

Saves a cache of {file_path: summary} to avoid re-generating on re-runs.

Usage:
    python scripts/ingestion/contextual_enrichment.py \
        --data-dir data/raw \
        --llm-url http://localhost:8011/v1 \
        --cache data/enrichment_cache.jsonl
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Optional

import httpx

CONTEXT_PROMPT = """Ești un asistent academic. Citește documentul de mai jos și scrie un rezumat SCURT (2-3 propoziții) care descrie:
- Ce subiect academic acoperă acest document
- Pentru ce curs / domeniu este relevant
- Ce tipuri de informații conține (definiții, exemple, teorii, etc.)

Scrie DOAR rezumatul, fără titlu sau explicații suplimentare. Folosește aceeași limbă ca documentul.

DOCUMENT (primele 3000 caractere):
\"\"\"
{text}
\"\"\"

Rezumat:"""


async def summarize_document(
    client: httpx.AsyncClient,
    llm_url: str,
    model: str,
    file_path: Path,
) -> Optional[str]:
    text = file_path.read_text(encoding="utf-8", errors="ignore")[:3000]
    if len(text.strip()) < 100:
        return None

    prompt = CONTEXT_PROMPT.format(text=text)
    try:
        resp = await client.post(
            f"{llm_url}/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.1,
            },
            timeout=60,
        )
        resp.raise_for_status()
        summary = resp.json()["choices"][0]["message"]["content"].strip()
        return summary
    except Exception as e:
        print(f"  [error] {file_path.name}: {e}", file=sys.stderr)
        return None


async def async_main(args: argparse.Namespace) -> None:
    data_dir = Path(args.data_dir)
    cache_path = Path(args.cache)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing cache
    cache: Dict[str, str] = {}
    if cache_path.exists():
        with open(cache_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    cache[rec["file"]] = rec["summary"]
        print(f"Loaded {len(cache)} cached summaries")

    # Collect all files
    files = []
    for course_dir in sorted(data_dir.iterdir()):
        if not course_dir.is_dir():
            continue
        for ext in [".txt", ".md"]:
            files.extend(course_dir.glob(f"**/*{ext}"))

    to_process = [f for f in files if str(f) not in cache]
    print(f"Files to summarize: {len(to_process)} (cached: {len(cache)})")

    if not to_process:
        print("All files already cached.")
        return

    # Detect model
    async with httpx.AsyncClient() as probe:
        try:
            resp = await probe.get(f"{args.llm_url}/models", timeout=10)
            model = resp.json()["data"][0]["id"]
            print(f"Model: {model}")
        except Exception:
            model = args.model

    # Process files
    async with httpx.AsyncClient() as client:
        with open(cache_path, "a", encoding="utf-8") as out:
            for i, file_path in enumerate(to_process, 1):
                print(f"  [{i:2d}/{len(to_process)}] {file_path.name}")
                summary = await summarize_document(client, args.llm_url, model, file_path)
                if summary:
                    rec = {"file": str(file_path), "summary": summary}
                    cache[str(file_path)] = summary
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    out.flush()
                    print(f"         → {summary[:80]}...")

    print(f"\nDone. {len(cache)} summaries saved to {cache_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate document context summaries")
    parser.add_argument("--data-dir",  default="data/raw")
    parser.add_argument("--llm-url",   default="http://localhost:8011/v1")
    parser.add_argument("--model",     default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--cache",     default="data/enrichment_cache.jsonl")
    args = parser.parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
