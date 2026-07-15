#!/usr/bin/env python3
"""
Generate a QA evaluation dataset from raw course materials.

For each text chunk it calls the LLM to produce question/answer pairs
where the answer is explicitly grounded in that chunk.  This gives you
a "gold" dataset you can later use to measure RAG accuracy.

Output format (JSONL, one JSON object per line):
  {
    "id":          "filos-2026__01_filosofie__0",
    "course_id":   "FILOS-2026",
    "source_file": "01_filosofie_introducere.txt",
    "chunk_text":  "...",
    "question":    "...",
    "gold_answer": "...",
    "language":    "ro"
  }

Usage:
    # All courses, 3 QA pairs per chunk, sample 10 chunks per file
    python scripts/evaluation/generate_dataset.py \\
        --data-dir data/raw \\
        --llm-url http://localhost:8001/v1 \\
        --output data/eval_dataset.jsonl

    # Single course
    python scripts/evaluation/generate_dataset.py \\
        --data-dir data/raw/FILOS-2026 \\
        --llm-url http://localhost:8001/v1 \\
        --output data/filos_dataset.jsonl \\
        --chunks-per-file 5 \\
        --qa-per-chunk 2
"""

import argparse
import asyncio
import json
import random
import sys
from pathlib import Path
from typing import List, Optional

import httpx

# ---------------------------------------------------------------------------
# Prompt sent to the LLM for each chunk
# ---------------------------------------------------------------------------
QA_GENERATION_PROMPT = """Ești un profesor universitar. Citește textul de mai jos și generează exact {n} perechi întrebare-răspuns.

REGULI STRICTE:
1. Întrebarea trebuie să fie ceva ce ar putea întreba un student despre CONȚINUTUL academic.
2. Răspunsul trebuie să fie EXCLUSIV din textul dat — fără cunoștințe externe.
3. Răspunsul trebuie să fie complet și detaliat (3-6 propoziții).
4. Folosește aceeași limbă ca textul (română/rusă/engleză).
5. Returnează DOAR JSON valid, fără explicații suplimentare.

INTERZIS — nu genera întrebări despre:
- Sursa textului, autorul, instituția, cursul sau anul academic
- Link-uri externe, referințe bibliografice, note de subsol
- Metadate: "Ce subiect abordează acest text?", "De unde provine?", "Ce conține documentul?"
- Informații despre Wikipedia, arhive sau surse secundare

PERMIS — întrebări despre concepte, definiții, exemple, cauze, efecte, diferențe, argumente din text.

Format JSON obligatoriu:
[
  {{"question": "...", "answer": "..."}},
  {{"question": "...", "answer": "..."}}
]

TEXT:
\"\"\"
{chunk}
\"\"\"

JSON:"""


# ---------------------------------------------------------------------------
# Text splitter (mirrors document_processor._split_text)
# ---------------------------------------------------------------------------
def split_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        if len(para) > chunk_size:
            if current:
                chunks.append(current.strip())
                current = ""
            words = para.split()
            temp = ""
            for word in words:
                if len(temp) + len(word) + 1 <= chunk_size:
                    temp += (" " if temp else "") + word
                else:
                    if temp:
                        chunks.append(temp.strip())
                    temp = word
            if temp:
                current = temp
        elif len(current) + len(para) + 2 <= chunk_size:
            current += ("\n\n" if current else "") + para
        else:
            if current:
                chunks.append(current.strip())
            current = para

    if current:
        chunks.append(current.strip())

    return chunks or [text]


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------
async def call_llm(
    client: httpx.AsyncClient,
    llm_url: str,
    model: str,
    prompt: str,
    timeout: int = 60,
) -> Optional[str]:
    try:
        resp = await client.post(
            f"{llm_url}/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024,
                "temperature": 0.3,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"    [LLM error] {e}", file=sys.stderr)
        return None


def parse_qa_json(raw: str) -> List[dict]:
    """Extract the JSON array from LLM output (may contain surrounding text)."""
    raw = raw.strip()
    # Find first '[' and last ']'
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        pairs = json.loads(raw[start : end + 1])
        return [p for p in pairs if isinstance(p, dict) and "question" in p and "answer" in p]
    except json.JSONDecodeError:
        return []


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------
async def process_file(
    client: httpx.AsyncClient,
    llm_url: str,
    model: str,
    file_path: Path,
    course_id: str,
    chunks_per_file: int,
    qa_per_chunk: int,
) -> List[dict]:
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    all_chunks = split_text(text)

    # Sample evenly across the file
    if len(all_chunks) > chunks_per_file:
        step = len(all_chunks) / chunks_per_file
        indices = [int(i * step) for i in range(chunks_per_file)]
        selected = [all_chunks[i] for i in indices]
    else:
        selected = all_chunks

    records: List[dict] = []
    for chunk_idx, chunk in enumerate(selected):
        if len(chunk.strip()) < 100:  # skip very short chunks
            continue

        prompt = QA_GENERATION_PROMPT.format(n=qa_per_chunk, chunk=chunk)
        raw = await call_llm(client, llm_url, model, prompt)
        if not raw:
            continue

        pairs = parse_qa_json(raw)
        for pair_idx, pair in enumerate(pairs[:qa_per_chunk]):
            record_id = f"{course_id}__{file_path.stem}__{chunk_idx}__{pair_idx}"
            records.append({
                "id": record_id,
                "course_id": course_id,
                "source_file": file_path.name,
                "chunk_text": chunk,
                "question": pair["question"].strip(),
                "gold_answer": pair["answer"].strip(),
                "language": "ro",  # all current materials are in Romanian
            })

        print(f"    chunk {chunk_idx}: {len(pairs)} QA pairs generated")

    return records


async def async_main(args: argparse.Namespace) -> None:
    data_dir = Path(args.data_dir)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Find all course directories or treat data_dir itself as one course
    if (data_dir / "*.txt").parent == data_dir and any(data_dir.glob("*.txt")):
        course_dirs = [data_dir]
    else:
        course_dirs = [d for d in data_dir.iterdir() if d.is_dir()]

    if not course_dirs:
        print(f"No course directories found in {data_dir}")
        sys.exit(1)

    # Detect model name from vLLM
    async with httpx.AsyncClient() as probe:
        try:
            resp = await probe.get(f"{args.llm_url}/models", timeout=10)
            model = resp.json()["data"][0]["id"]
            print(f"Using model: {model}")
        except Exception:
            model = args.model
            print(f"Using model (fallback): {model}")

    all_records: List[dict] = []

    async with httpx.AsyncClient() as client:
        for course_dir in sorted(course_dirs):
            course_id = course_dir.name
            files = list(course_dir.glob("**/*.txt")) + list(course_dir.glob("**/*.md"))
            if not files:
                continue

            print(f"\nCourse: {course_id}  ({len(files)} files)")

            if args.shuffle:
                random.shuffle(files)

            files_to_process = files[: args.max_files] if args.max_files else files

            for file_path in files_to_process:
                print(f"  {file_path.name}")
                records = await process_file(
                    client=client,
                    llm_url=args.llm_url,
                    model=model,
                    file_path=file_path,
                    course_id=course_id,
                    chunks_per_file=args.chunks_per_file,
                    qa_per_chunk=args.qa_per_chunk,
                )
                all_records.extend(records)
                print(f"  -> {len(records)} QA pairs (total so far: {len(all_records)})")

    # Write JSONL
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\nDataset saved: {output_path}")
    print(f"Total QA pairs: {len(all_records)}")
    courses = {r["course_id"] for r in all_records}
    for cid in sorted(courses):
        n = sum(1 for r in all_records if r["course_id"] == cid)
        print(f"  {cid}: {n} pairs")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate QA evaluation dataset from course materials")
    parser.add_argument("--data-dir",       default="data/raw",                   help="Raw course materials directory")
    parser.add_argument("--llm-url",        default="http://localhost:8001/v1",    help="vLLM base URL")
    parser.add_argument("--model",          default="Qwen/Qwen2.5-7B-Instruct",   help="Model name fallback")
    parser.add_argument("--output",         default="data/eval_dataset.jsonl",    help="Output JSONL file")
    parser.add_argument("--chunks-per-file",type=int, default=8,                  help="Chunks sampled per file (default: 8)")
    parser.add_argument("--qa-per-chunk",   type=int, default=3,                  help="QA pairs per chunk (default: 3)")
    parser.add_argument("--max-files",      type=int, default=None,               help="Max files per course (default: all)")
    parser.add_argument("--shuffle",        action="store_true",                   help="Shuffle files before sampling")
    args = parser.parse_args()

    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
