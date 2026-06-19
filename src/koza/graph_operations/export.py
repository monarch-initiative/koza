"""Export / convert: write a koza DuckDB graph back out as single KGX files.

The inverse of load/join. `export` writes the canonical `nodes` / `edges` tables
to one file each in the requested format (it does NOT fragment by a field the way
`split` does). `convert` is `load` + `export` composed — a one-shot file-format
conversion, mirroring how `merge` = join + normalize + prune.

Serialization policy (the part a plain `SELECT * ... COPY` gets wrong on
provenance-rich edges, where a `sources` list-of-struct comes out as DuckDB's
struct-repr — neither valid JSON nor valid KGX):

- **TSV** — scalar multivalued columns (`VARCHAR[]`, `publications`, …) are
  ``|``-delimited per KGX convention; nested object columns (`sources` and other
  struct / map / json / list-of-list) are written as **JSON-in-cell** (there's no
  KGX standard for nested objects, and JSON round-trips losslessly).
- **JSONL / Parquet** — keep nested data natively; copied as-is.
"""

from __future__ import annotations

import time
from pathlib import Path

from loguru import logger

from koza.model.graph_operations import ConvertConfig, ExportConfig, ExportResult, KGXFormat

from .utils import GraphDatabase

_EXT = {KGXFormat.TSV: "tsv", KGXFormat.JSONL: "jsonl", KGXFormat.PARQUET: "parquet"}


def _existing_tables(conn) -> set[str]:
    return {r[0] for r in conn.execute("SELECT table_name FROM information_schema.tables").fetchall()}


def _tsv_column_expr(name: str, dtype: str) -> str:
    """Project one column for TSV per the serialization policy.

    Nested objects (struct / map / json / list-of-list) → JSON-in-cell; scalar
    lists → ``|``-delimited; scalars → as-is.
    """
    q = f'"{name}"'
    up = dtype.upper().strip()
    if "STRUCT" in up or "MAP" in up or up == "JSON":
        return f"to_json({q}) AS {q}"
    if up.endswith("[]"):
        if up[:-2].endswith("]"):  # list-of-list → JSON
            return f"to_json({q}) AS {q}"
        return f"array_to_string({q}::VARCHAR[], '|') AS {q}"  # scalar list → KGX pipe-join
    return q


def _export_table(db: GraphDatabase, table: str, path: Path, fmt: KGXFormat) -> int:
    """COPY one table to one file, applying the TSV serialization policy."""
    if fmt == KGXFormat.TSV:
        cols = db.conn.execute(f"DESCRIBE {table}").fetchall()
        select = ", ".join(_tsv_column_expr(c[0], c[1]) for c in cols)
        # FORMAT CSV so the format is authoritative regardless of the file suffix.
        db.conn.execute(
            f"COPY (SELECT {select} FROM {table}) TO '{path}' (FORMAT CSV, HEADER, DELIMITER '\\t')"
        )
    elif fmt == KGXFormat.PARQUET:
        db.conn.execute(f"COPY (SELECT * FROM {table}) TO '{path}' (FORMAT PARQUET)")
    elif fmt == KGXFormat.JSONL:
        db.conn.execute(f"COPY (SELECT * FROM {table}) TO '{path}' (FORMAT JSON)")
    else:
        raise ValueError(f"Unsupported output format: {fmt}")
    return db.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def export_graph(config: ExportConfig) -> ExportResult:
    """Write a koza DuckDB graph's tables out as single KGX files.

    By default exports whichever of `nodes` / `edges` exist; override with
    `config.tables`. Returns the files written and their row counts.
    """
    start = time.time()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    ext = _EXT[config.output_format]

    out_files: list[Path] = []
    counts: dict[str, int] = {}
    with GraphDatabase(config.database_path, read_only=True) as db:
        present = _existing_tables(db.conn)
        tables = config.tables or [t for t in ("nodes", "edges") if t in present]
        for table in tables:
            if table not in present:
                logger.warning(f"Table '{table}' not in {config.database_path}, skipping")
                continue
            path = config.output_dir / f"{table}.{ext}"
            counts[table] = _export_table(db, table, path, config.output_format)
            out_files.append(path)
            if not config.quiet:
                logger.info(f"Exported {counts[table]:,} {table} -> {path}")

    return ExportResult(
        output_files=out_files,
        row_counts=counts,
        output_format=config.output_format,
        total_time_seconds=time.time() - start,
    )


def convert_graph(config: ConvertConfig) -> ExportResult:
    """One-shot KGX format conversion: load the input files into a temporary
    DuckDB, then export them. Equivalent to `koza load` followed by `koza export`.
    """
    import os
    import tempfile

    from .load import load_graph, prepare_load_config_from_paths

    start = time.time()
    tmp_dir = Path(tempfile.mkdtemp(prefix="koza-convert-"))
    tmp_db = tmp_dir / "convert.duckdb"
    try:
        load_cfg = prepare_load_config_from_paths(
            node_files=config.node_files,
            edge_files=config.edge_files,
            output_database=tmp_db,
            slots_file=config.slots_file,
            seed_schema=False,  # not needed for a plain conversion; skips the Biolink load
            quiet=config.quiet,
            show_progress=False,
        )
        load_graph(load_cfg)
        result = export_graph(
            ExportConfig(
                database_path=tmp_db,
                output_dir=config.output_dir,
                output_format=config.output_format,
                quiet=config.quiet,
            )
        )
    finally:
        if tmp_db.exists():
            tmp_db.unlink()
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass

    result.total_time_seconds = time.time() - start
    return result
