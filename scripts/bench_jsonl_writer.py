"""Synthetic benchmark for JSONL writer hot path.

Compares strategies for serializing dicts to a JSONL file:
  - json.dumps + text write + "\n"  (current koza approach)
  - orjson.dumps + binary write (uses orjson.OPT_APPEND_NEWLINE)
  - orjson.dumps + binary write, batched into one write() per N rows
  - msgspec.json.encode + binary write

Each strategy writes the same input set to a tempfile and we compare wall time
plus output equivalence.
"""

import json
import os
import tempfile
import time
from pathlib import Path

import orjson
import msgspec.json

N_EDGES = 500_000
BATCH_SIZE = 1000


def make_edge(i: int) -> dict:
    return {
        "id": f"uuid:{i:08d}",
        "category": ["biolink:Association"],
        "subject": f"NCBIGene:{i % 100000}",
        "predicate": "biolink:related_to",
        "object": f"MONDO:{(i * 7) % 50000:07d}",
        "knowledge_level": "knowledge_assertion",
        "agent_type": "manual_agent",
        "primary_knowledge_source": "infores:example",
        "aggregator_knowledge_source": ["infores:monarchinitiative"],
        "publications": [f"PMID:{i + 1000}", f"PMID:{i + 2000}"],
        "qualifiers": [],
    }


def bench_json_text(rows, path):
    start = time.perf_counter()
    with open(path, "w") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return time.perf_counter() - start


def bench_orjson_binary(rows, path):
    start = time.perf_counter()
    with open(path, "wb") as fh:
        for row in rows:
            fh.write(orjson.dumps(row, option=orjson.OPT_APPEND_NEWLINE))
    return time.perf_counter() - start


def bench_orjson_batched(rows, path, batch_size=BATCH_SIZE):
    start = time.perf_counter()
    with open(path, "wb") as fh:
        buf = []
        for row in rows:
            buf.append(orjson.dumps(row, option=orjson.OPT_APPEND_NEWLINE))
            if len(buf) >= batch_size:
                fh.write(b"".join(buf))
                buf.clear()
        if buf:
            fh.write(b"".join(buf))
    return time.perf_counter() - start


def bench_msgspec(rows, path):
    encoder = msgspec.json.Encoder()
    start = time.perf_counter()
    with open(path, "wb") as fh:
        for row in rows:
            fh.write(encoder.encode(row) + b"\n")
    return time.perf_counter() - start


def normalize(path: Path) -> list[dict]:
    """Load JSONL back to dicts so byte-level differences (key order) don't fail equivalence."""
    out = []
    with open(path, "rb") as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line))
    return out


def main():
    print(f"Generating {N_EDGES:,} synthetic edges...")
    rows = [make_edge(i) for i in range(N_EDGES)]

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        baseline_path = tdp / "json_text.jsonl"

        runs = [
            ("json.dumps + text write (current)", bench_json_text, baseline_path),
            ("orjson + binary write", bench_orjson_binary, tdp / "orjson.jsonl"),
            (f"orjson + batched (n={BATCH_SIZE}) writes", bench_orjson_batched, tdp / "orjson_batch.jsonl"),
            ("msgspec.json + binary write", bench_msgspec, tdp / "msgspec.jsonl"),
        ]

        results = []
        for label, fn, path in runs:
            elapsed = fn(rows, path)
            size_mb = os.path.getsize(path) / (1024 * 1024)
            results.append((label, elapsed, size_mb, path))

        baseline_time = results[0][1]
        print(f"\n{'Strategy':<45} {'Time (s)':>10} {'Rows/s':>14} {'MB':>10} {'Speedup':>10}")
        print("-" * 95)
        for label, elapsed, size_mb, _ in results:
            rps = N_EDGES / elapsed
            speedup = baseline_time / elapsed
            print(f"{label:<45} {elapsed:>10.3f} {rps:>14,.0f} {size_mb:>10.2f} {speedup:>9.2f}x")

        print("\nVerifying output equivalence (re-parsed dicts)...")
        baseline = normalize(results[0][3])
        for label, _, _, path in results[1:]:
            other = normalize(path)
            if baseline == other:
                print(f"  OK  {label}")
            else:
                # Find first divergence
                for i, (a, b) in enumerate(zip(baseline, other)):
                    if a != b:
                        print(f"  DIFF {label} at row {i}:\n    base:  {a}\n    other: {b}")
                        break
                else:
                    print(f"  DIFF {label}: length mismatch {len(baseline)} vs {len(other)}")


if __name__ == "__main__":
    main()
