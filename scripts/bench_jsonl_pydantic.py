"""Benchmark JSONL writing of pydantic Association models.

Mirrors the path used by koza's JSONLWriter:
  Association (pydantic v2) -> dict (model_dump) -> JSON string -> file write

Compares strategies that bypass the model_dump intermediate dict.
"""

import json
import os
import tempfile
import time
from pathlib import Path

import orjson
from biolink_model.datamodel.pydanticmodel_v2 import Association

N_EDGES = 100_000
BATCH_SIZE = 1000


def make_association(i: int) -> Association:
    return Association(
        id=f"uuid:{i:08d}",
        category=["biolink:Association"],
        subject=f"NCBIGene:{i % 100000}",
        predicate="biolink:related_to",
        object=f"MONDO:{(i * 7) % 50000:07d}",
        knowledge_level="knowledge_assertion",
        agent_type="manual_agent",
        primary_knowledge_source="infores:example",
        aggregator_knowledge_source=["infores:monarchinitiative"],
        publications=[f"PMID:{i + 1000}", f"PMID:{i + 2000}"],
    )


def bench_current(rows, path):
    """Current koza: model_dump(mode='json', exclude_none=True) + json.dumps + text write."""
    start = time.perf_counter()
    with open(path, "w") as fh:
        for row in rows:
            d = row.model_dump(mode="json", exclude_none=True)
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    return time.perf_counter() - start


def bench_dump_orjson(rows, path):
    """model_dump + orjson + binary write."""
    start = time.perf_counter()
    with open(path, "wb") as fh:
        for row in rows:
            d = row.model_dump(mode="json", exclude_none=True)
            fh.write(orjson.dumps(d, option=orjson.OPT_APPEND_NEWLINE))
    return time.perf_counter() - start


def bench_pydantic_to_json(rows, path):
    """Pydantic's own serializer: model.__pydantic_serializer__.to_json(...) -> bytes.
    Bypasses the intermediate Python dict entirely."""
    serializer = Association.__pydantic_serializer__
    start = time.perf_counter()
    with open(path, "wb") as fh:
        for row in rows:
            fh.write(serializer.to_json(row, exclude_none=True))
            fh.write(b"\n")
    return time.perf_counter() - start


def bench_pydantic_to_json_batched(rows, path, batch_size=BATCH_SIZE):
    """Pydantic serializer + batched writes."""
    serializer = Association.__pydantic_serializer__
    start = time.perf_counter()
    with open(path, "wb") as fh:
        buf = []
        for row in rows:
            buf.append(serializer.to_json(row, exclude_none=True))
            buf.append(b"\n")
            if len(buf) >= batch_size * 2:
                fh.write(b"".join(buf))
                buf.clear()
        if buf:
            fh.write(b"".join(buf))
    return time.perf_counter() - start


def bench_model_dump_json(rows, path):
    """Pydantic's model_dump_json() (returns str, has to encode again)."""
    start = time.perf_counter()
    with open(path, "w") as fh:
        for row in rows:
            fh.write(row.model_dump_json(exclude_none=True) + "\n")
    return time.perf_counter() - start


def normalize(path: Path) -> list[dict]:
    out = []
    with open(path, "rb") as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line))
    return out


def main():
    print(f"Generating {N_EDGES:,} pydantic Association models...")
    rows = [make_association(i) for i in range(N_EDGES)]

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        runs = [
            ("current: model_dump + json.dumps + text", bench_current, tdp / "current.jsonl"),
            ("model_dump + orjson + binary", bench_dump_orjson, tdp / "dump_orjson.jsonl"),
            ("pydantic serializer to_json (no dict)", bench_pydantic_to_json, tdp / "pyd.jsonl"),
            (f"pydantic to_json + batched (n={BATCH_SIZE})", bench_pydantic_to_json_batched, tdp / "pyd_batch.jsonl"),
            ("model_dump_json (text)", bench_model_dump_json, tdp / "mdj.jsonl"),
        ]

        results = []
        for label, fn, path in runs:
            elapsed = fn(rows, path)
            size_mb = os.path.getsize(path) / (1024 * 1024)
            results.append((label, elapsed, size_mb, path))

        baseline_time = results[0][1]
        print(f"\n{'Strategy':<48} {'Time (s)':>10} {'Rows/s':>14} {'MB':>10} {'Speedup':>10}")
        print("-" * 95)
        for label, elapsed, size_mb, _ in results:
            rps = N_EDGES / elapsed
            speedup = baseline_time / elapsed
            print(f"{label:<48} {elapsed:>10.3f} {rps:>14,.0f} {size_mb:>10.2f} {speedup:>9.2f}x")

        print("\nVerifying output equivalence (re-parsed dicts)...")
        baseline = normalize(results[0][3])
        for label, _, _, path in results[1:]:
            other = normalize(path)
            if baseline == other:
                print(f"  OK  {label}")
            else:
                for i, (a, b) in enumerate(zip(baseline, other)):
                    if a != b:
                        print(f"  DIFF {label} at row {i}:")
                        # Show only differing keys
                        diff_keys = set(a) ^ set(b)
                        for k in diff_keys:
                            print(f"    key={k!r}: base={a.get(k)!r} other={b.get(k)!r}")
                        for k in set(a) & set(b):
                            if a[k] != b[k]:
                                print(f"    key={k!r}: base={a[k]!r} other={b[k]!r}")
                        break
                else:
                    print(f"  DIFF {label}: length mismatch {len(baseline)} vs {len(other)}")


if __name__ == "__main__":
    main()
