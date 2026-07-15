#!/usr/bin/env python3
"""
Latency benchmark for the RAG chatbot API.

Measures p50/p95/p99 latency per stage (embed / search / llm / total),
tests cache behaviour, and optionally stresses with concurrent requests.

Usage:
    # Sequential, 20 requests, no cache
    python scripts/testing/benchmark.py --url http://localhost:8010 -n 20

    # Include concurrency test (5 parallel workers)
    python scripts/testing/benchmark.py --url http://localhost:8010 -n 20 --concurrency 5

    # Target a specific course
    python scripts/testing/benchmark.py --url http://localhost:8010 --course-id ASD-2024

    # Save raw CSV for later comparison
    python scripts/testing/benchmark.py --url http://localhost:8010 --csv results_before.csv
"""

import argparse
import asyncio
import csv
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import httpx

QUESTIONS = [
    "Что такое двоичное дерево поиска?",
    "Объясни принцип работы быстрой сортировки",
    "Какие методы есть в объектно-ориентированном программировании?",
    "Что такое рекурсия и как она работает?",
    "Объясни разницу между стеком и очередью",
    "Что такое алгоритм Дейкстры?",
    "Как работает хэш-таблица?",
    "Что такое динамическое программирование?",
    "Объясни разницу между TCP и UDP",
    "Что такое нормализация базы данных?",
]


def percentile(data: List[float], p: int) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(sorted_data) - 1)
    return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (k - lo)


def print_stats(label: str, values: List[float], unit: str = "ms") -> None:
    if not values:
        print(f"  {label:12s}  no data")
        return
    print(
        f"  {label:12s}  "
        f"p50={percentile(values, 50):7.0f}{unit}  "
        f"p95={percentile(values, 95):7.0f}{unit}  "
        f"p99={percentile(values, 99):7.0f}{unit}  "
        f"mean={statistics.mean(values):7.0f}{unit}  "
        f"min={min(values):7.0f}{unit}  "
        f"max={max(values):7.0f}{unit}"
    )


async def send_request(
    client: httpx.AsyncClient,
    url: str,
    question: str,
    course_id: Optional[str],
) -> Dict:
    payload = {"question": question, "language": "ru"}
    if course_id:
        payload["course_id"] = course_id

    t0 = time.perf_counter()
    try:
        resp = await client.post(f"{url}/api/chat", json=payload, timeout=120)
        wall_ms = (time.perf_counter() - t0) * 1000
        resp.raise_for_status()
        data = resp.json()
        timing = data.get("timing") or {}
        return {
            "ok": True,
            "cached": data.get("cached", False),
            "wall_ms": wall_ms,
            "embed_ms": timing.get("embed_ms"),
            "search_ms": timing.get("search_ms"),
            "llm_ms": timing.get("llm_ms"),
            "total_ms": timing.get("total_ms"),
            "answer_len": len(data.get("answer", "")),
        }
    except Exception as e:
        wall_ms = (time.perf_counter() - t0) * 1000
        return {"ok": False, "error": str(e), "wall_ms": wall_ms}


async def run_sequential(
    url: str,
    n: int,
    course_id: Optional[str],
    clear_cache: bool,
) -> List[Dict]:
    results = []
    async with httpx.AsyncClient() as client:
        if clear_cache:
            try:
                await client.post(f"{url}/api/cache/clear", timeout=10)
                print("  Cache cleared.")
            except Exception:
                pass

        questions = [QUESTIONS[i % len(QUESTIONS)] for i in range(n)]
        for i, q in enumerate(questions, 1):
            r = await send_request(client, url, q, course_id)
            results.append(r)
            status = "CACHE" if r.get("cached") else "LLM  "
            total = r.get("total_ms") or r["wall_ms"]
            ok = "OK" if r["ok"] else f"ERR {r.get('error', '')[:40]}"
            print(f"  [{i:3d}/{n}] {status}  total={total:6.0f}ms  {ok}")

    return results


async def run_concurrent(
    url: str,
    n: int,
    concurrency: int,
    course_id: Optional[str],
) -> List[Dict]:
    """Fire `n` requests with `concurrency` workers, measure throughput."""
    results = []
    sem = asyncio.Semaphore(concurrency)
    questions = [QUESTIONS[i % len(QUESTIONS)] for i in range(n)]

    async def worker(client: httpx.AsyncClient, q: str) -> Dict:
        async with sem:
            return await send_request(client, url, q, course_id)

    t_start = time.perf_counter()
    async with httpx.AsyncClient() as client:
        tasks = [asyncio.create_task(worker(client, q)) for q in questions]
        results = await asyncio.gather(*tasks, return_exceptions=False)
    elapsed = time.perf_counter() - t_start

    ok_count = sum(1 for r in results if r.get("ok"))
    rps = n / elapsed
    print(f"  {n} requests in {elapsed:.1f}s  →  {rps:.2f} req/s  ({ok_count}/{n} OK)")
    return list(results)


def summarise(results: List[Dict]) -> None:
    ok = [r for r in results if r.get("ok")]
    errors = len(results) - len(ok)
    cached = sum(1 for r in ok if r.get("cached"))

    print(f"\n  Requests: {len(results)}  OK: {len(ok)}  Errors: {errors}  Cache hits: {cached}/{len(ok)}")
    print()

    wall   = [r["wall_ms"]   for r in ok]
    total  = [r["total_ms"]  for r in ok if r.get("total_ms")]
    embed  = [r["embed_ms"]  for r in ok if r.get("embed_ms")]
    search = [r["search_ms"] for r in ok if r.get("search_ms")]
    llm    = [r["llm_ms"]    for r in ok if r.get("llm_ms")]

    # Separate cached vs non-cached for total/llm
    total_fresh  = [r["total_ms"] for r in ok if r.get("total_ms") and not r.get("cached")]
    total_cached = [r["wall_ms"]  for r in ok if r.get("cached")]

    print_stats("wall",         wall)
    print_stats("total (api)",  total)
    if total_fresh:
        print_stats("total:fresh",  total_fresh)
    if total_cached:
        print_stats("total:cached", total_cached)
    print_stats("embed",        embed)
    print_stats("search",       search)
    print_stats("llm",          llm)


def save_csv(results: List[Dict], path: str) -> None:
    fields = ["ok", "cached", "wall_ms", "embed_ms", "search_ms", "llm_ms", "total_ms", "answer_len", "error"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)
    print(f"\n  Saved raw data → {path}")


def compare_csv(before_path: str, after_path: str) -> None:
    def load(path: str) -> List[Dict]:
        with open(path) as f:
            return [r for r in csv.DictReader(f) if r["ok"] == "True" and r["total_ms"]]

    before = load(before_path)
    after  = load(after_path)

    def vals(rows, key):
        return [float(r[key]) for r in rows if r.get(key)]

    print(f"\n{'':=<70}")
    print(f"  BEFORE: {before_path}  ({len(before)} ok samples)")
    print(f"  AFTER:  {after_path}  ({len(after)} ok samples)")
    print(f"{'':=<70}")
    print(f"  {'stage':12s}  {'before p50':>12}  {'after p50':>12}  {'delta':>10}  {'speedup':>8}")
    print(f"  {'-'*65}")

    for key, label in [("total_ms", "total"), ("embed_ms", "embed"),
                        ("search_ms", "search"), ("llm_ms", "llm")]:
        b = vals(before, key)
        a = vals(after, key)
        if not b or not a:
            continue
        bp50 = percentile(b, 50)
        ap50 = percentile(a, 50)
        delta = ap50 - bp50
        speedup = bp50 / ap50 if ap50 else float("inf")
        sign = "+" if delta > 0 else ""
        print(f"  {label:12s}  {bp50:>12.0f}ms  {ap50:>12.0f}ms  {sign}{delta:>8.0f}ms  {speedup:>7.2f}x")
    print(f"{'':=<70}\n")


async def async_main(args: argparse.Namespace) -> None:
    if args.compare:
        before, after = args.compare
        compare_csv(before, after)
        return

    url = args.url.rstrip("/")
    print(f"\n{'':=<70}")
    print(f"  Benchmark target: {url}")
    print(f"  Requests:         {args.n}")
    if args.course_id:
        print(f"  Course filter:    {args.course_id}")
    print(f"{'':=<70}\n")

    # --- Sequential ---
    print("SEQUENTIAL (cold cache):")
    seq_results = await run_sequential(url, args.n, args.course_id, clear_cache=True)
    summarise(seq_results)

    # --- Cache warm-up + repeat ---
    print("\nSEQUENTIAL (warm cache — same questions repeated):")
    seq_cached = await run_sequential(url, args.n, args.course_id, clear_cache=False)
    summarise(seq_cached)

    # --- Concurrent ---
    if args.concurrency and args.concurrency > 1:
        print(f"\nCONCURRENT ({args.concurrency} workers, {args.n} requests):")
        await run_concurrent(url, args.n, args.concurrency, args.course_id)

    if args.csv:
        save_csv(seq_results, args.csv)
        print(f"  (To compare later: --compare {args.csv} results_after.csv)")

    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG chatbot latency benchmark")
    parser.add_argument("--url", default="http://localhost:8010", help="API base URL")
    parser.add_argument("-n", type=int, default=20, help="Number of requests (default: 20)")
    parser.add_argument("--course-id", help="Filter by course ID")
    parser.add_argument("--concurrency", type=int, default=0, help="Concurrent workers (0 = sequential only)")
    parser.add_argument("--csv", help="Save raw results to CSV for later comparison")
    parser.add_argument("--compare", nargs=2, metavar=("BEFORE.csv", "AFTER.csv"),
                        help="Compare two CSV files and print speedup table")
    args = parser.parse_args()

    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
