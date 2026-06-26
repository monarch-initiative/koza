"""Graph profiling: "tell me about the shape of this graph".

The core piece is `detect_categorical_columns` — a schema-smart classifier that
decides which columns of a koza table are worth grouping on, combining Biolink
schema signals with a DuckDB cardinality probe:

- **Schema (Biolink slot hierarchy + range)** gives high-confidence verdicts:
  enum / boolean ranges and slots descending from ``type`` (category) or
  ``knowledge source`` are categorical; identifier slots and free-text ranges
  (``label type`` / ``narrative text``) are not.
- **Cardinality (DuckDB ``approx_count_distinct``)** decides the ambiguous middle
  — class-ranged slots that may still be low-cardinality (``in_taxon``),
  non-Biolink derived columns (``subject_category``, ``*_closure``), and any
  column on an unseeded graph where no schema is available.

`profile_table` builds per-column marginal distributions over the detected
categoricals; `profile.py`'s consumers (CLI) render those in the terminal.
"""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

# Biolink slot ancestors that mark a slot as categorical regardless of range.
_CATEGORICAL_ANCESTORS = {"type", "knowledge source"}
# Biolink ranges that are free text — never categorical.
_TEXTLIKE_RANGES = {"label type", "narrative text"}
# Biolink numeric ranges — measurements, never categorical (note: KGX TSV often
# stores these as VARCHAR, so the schema range is the reliable signal, not the
# DuckDB column type).
_NUMERIC_RANGES = {"integer", "double", "float", "decimal"}

# Suffix conventions for non-Biolink, closurize-derived columns. Excludes only
# (the safe direction); inclusion is left to the cardinality probe.
_DERIVED_EXCLUDE_SUFFIXES = ("_closure", "_closure_label", "_label", "_name")

# DuckDB numeric type prefixes — numeric columns are out of scope for the
# *categorical* probe (a low-cardinality count is a histogram, not a category).
_NUMERIC_TYPE_PREFIXES = (
    "TINYINT", "SMALLINT", "INTEGER", "BIGINT", "HUGEINT", "UTINYINT", "USMALLINT",
    "UINTEGER", "UBIGINT", "UHUGEINT", "FLOAT", "DOUBLE", "REAL", "DECIMAL", "NUMERIC",
)


def _is_numeric(dtype: str) -> bool:
    up = dtype.upper().lstrip("[]")
    return up.startswith(_NUMERIC_TYPE_PREFIXES)


@dataclass
class CategoricalColumn:
    """A column judged worth grouping on, with the signal that decided it."""

    name: str
    distinct_count: int
    is_list: bool  # VARCHAR[] etc. — marginals must UNNEST before grouping
    reason: str  # enum | boolean | type | knowledge_source | predicate | cardinality


def _schema_verdict(column: str, sv) -> str:
    """Classify a column from the Biolink schema alone.

    Returns ``"categorical"``, ``"exclude"``, or ``"probe"`` (defer to
    cardinality). ``sv`` is a Biolink SchemaView, or None when no schema is
    available — in which case everything is probed.
    """
    if sv is None:
        return "probe"

    bl = column.replace("_", " ")
    try:
        all_slots = sv.all_slots()
    except Exception:
        return "probe"
    if bl not in all_slots:
        # Non-Biolink (derived/custom) column: convention excludes, else probe.
        if column.endswith(_DERIVED_EXCLUDE_SUFFIXES):
            return "exclude"
        return "probe"

    slot = sv.get_slot(bl)
    if slot is None:
        return "probe"

    # Identifier slots (id, ...) are never categorical.
    if getattr(slot, "identifier", False):
        return "exclude"
    # `designates_type` (e.g. `category`) IS the category designator — the
    # strongest categorical signal, not an exclusion.
    if getattr(slot, "designates_type", False):
        return "categorical"

    rng = slot.range
    try:
        if rng in sv.all_enums():
            return "categorical"
    except Exception:
        pass
    if rng == "boolean":
        return "categorical"
    if rng in _TEXTLIKE_RANGES or rng in _NUMERIC_RANGES:
        return "exclude"
    # `named thing` is the entity root — slots ranged on it (subject, object)
    # are arbitrary endpoint references, never categorical. (More specific
    # entity classes like `organism taxon` stay probeable — see below.)
    if rng == "named thing":
        return "exclude"

    if bl == "predicate":
        return "categorical"
    try:
        ancestors = set(sv.slot_ancestors(bl))
    except Exception:
        ancestors = set()
    if ancestors & _CATEGORICAL_ANCESTORS:
        return "categorical"

    # Class-ranged slots (entity references: subject, object, in_taxon,
    # publications, ...) vary wildly in cardinality — let the probe decide.
    return "probe"


def _describe(conn, table: str) -> list[tuple[str, str]]:
    return [(r[0], r[1]) for r in conn.execute(f"DESCRIBE {table}").fetchall()]


def detect_categorical_columns(
    conn,
    table: str,
    sv=None,
    *,
    max_distinct: int = 50,
    max_ratio: float = 0.01,
    max_distinct_ceiling: int = 1000,
) -> list[CategoricalColumn]:
    """Return the columns of `table` worth grouping on, schema-smart.

    Args:
        conn: a DuckDB connection.
        table: table or view name.
        sv: Biolink SchemaView for the schema signal (None → cardinality only).
        max_distinct: a probed column is categorical if it has at most this many
            distinct values …
        max_ratio: … or if distinct/row_count is at most this fraction (catches
            low-but-not-tiny categoricals like the knowledge-source vocabulary in
            a large graph).
        max_distinct_ceiling: hard cap on the ratio path — a probed column with
            more distinct values than this is never categorical, however small
            the ratio. Stops a 15M-row graph from admitting thousands-distinct
            identifier/text columns (`has_evidence`, `disease_context_qualifier`)
            that pass the ratio test. The schema floor (enum/category/etc.) is
            exempt; it's always kept.

    Columns with a high-confidence schema verdict (enum/boolean/type/knowledge
    source/predicate) are always included; identifier and free-text slots are
    always excluded. Everything else — and every column on an unseeded graph —
    is decided by cardinality. Constant columns (1 distinct) and effectively
    unique columns are dropped. STRUCT columns are skipped entirely.
    """
    cols = _describe(conn, table)
    total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    if total == 0:
        return []

    # Decide which columns to probe, and pre-resolve schema verdicts.
    probe_cols: list[tuple[str, bool]] = []  # (name, is_list)
    verdicts: dict[str, str] = {}
    for name, dtype in cols:
        up = dtype.upper()
        if "STRUCT" in up:
            continue  # not meaningfully groupable (e.g. `sources`)
        verdict = _schema_verdict(name, sv)
        if verdict == "exclude":
            continue
        # Numeric columns are categorical only if the schema says so (e.g. a
        # boolean/enum); a numeric reaching the cardinality probe is a count or
        # measurement, not a category — skip it.
        if verdict != "categorical" and _is_numeric(dtype):
            continue
        verdicts[name] = verdict
        probe_cols.append((name, up.endswith("[]")))

    if not probe_cols:
        return []

    # One scan for all distinct counts. UNNEST list columns so the count
    # reflects element cardinality (category=['biolink:Gene'] → 1 category).
    select_parts = []
    for name, is_list in probe_cols:
        if is_list:
            select_parts.append(
                f'(SELECT approx_count_distinct(x) FROM (SELECT UNNEST("{name}") AS x FROM {table})) AS "{name}"'
            )
        else:
            select_parts.append(f'approx_count_distinct("{name}") AS "{name}"')
    row = conn.execute(f"SELECT {', '.join(select_parts)} FROM {table}").fetchone()
    distinct = dict(zip([c[0] for c in probe_cols], row))

    results: list[CategoricalColumn] = []
    for name, is_list in probe_cols:
        n = distinct[name] or 0
        verdict = verdicts[name]
        if verdict == "categorical":
            # Keep schema-categoricals even when constant — "every edge is
            # agent_type=X" is meaningful shape. Drop only all-null (n==0).
            if n < 1:
                continue
            results.append(CategoricalColumn(name, n, is_list, _schema_reason(name, sv)))
        else:  # probe — cardinality decides
            # Drop constants (nothing to say) and perfectly-unique columns
            # (identifier-like: every row distinct is not a category).
            if n <= 1 or n >= total:
                continue
            if n > max_distinct_ceiling:
                continue  # too many distinct values to be a useful category
            if n <= max_distinct or (n / total) <= max_ratio:
                results.append(CategoricalColumn(name, n, is_list, "cardinality"))

    # Stable, readable order: fewest distinct values first.
    results.sort(key=lambda c: (c.distinct_count, c.name))
    return results


def _schema_reason(column: str, sv) -> str:
    """Best-effort label of *why* the schema judged a column categorical."""
    if sv is None:
        return "cardinality"
    bl = column.replace("_", " ")
    try:
        slot = sv.get_slot(bl)
        if slot is not None:
            if getattr(slot, "designates_type", False):
                return "category"
            if slot.range in sv.all_enums():
                return "enum"
            if slot.range == "boolean":
                return "boolean"
        if bl == "predicate":
            return "predicate"
        ancestors = set(sv.slot_ancestors(bl))
        if "knowledge source" in ancestors:
            return "knowledge_source"
        if "type" in ancestors:
            return "type"
    except Exception:
        pass
    return "categorical"


def _existing_tables(conn) -> set[str]:
    return {
        r[0] for r in conn.execute(
            "SELECT table_name FROM information_schema.tables"
        ).fetchall()
    }


def _auto_tables(conn) -> list[str]:
    """The koza data tables worth profiling by default.

    Prefer the denormalized view over its base table when present: it's a
    superset (all edge/node columns plus subject/object node properties —
    `subject_category`, `object_namespace`, taxa — which the base `edges`
    table can't have), so profiling both is redundant. Falls back to the base
    tables on a non-closurized graph.
    """
    present = _existing_tables(conn)
    chosen = [
        "denormalized_edges" if "denormalized_edges" in present else "edges",
        "denormalized_nodes" if "denormalized_nodes" in present else "nodes",
    ]
    return [t for t in chosen if t in present]


def _marginal(conn, table: str, col: "CategoricalColumn", limit: int | None):
    """Top values of one categorical column as (value_str, count), desc by count.

    List columns are UNNESTed so each element is counted. `limit=None` returns
    the full distribution.
    """
    lim = f" LIMIT {limit}" if limit is not None else ""
    if col.is_list:
        src = f'(SELECT UNNEST("{col.name}") AS v FROM {table})'
    else:
        src = f'(SELECT "{col.name}" AS v FROM {table})'
    rows = conn.execute(
        f"SELECT CAST(v AS VARCHAR) AS value, COUNT(*) AS n "
        f"FROM {src} GROUP BY 1 ORDER BY n DESC, value{lim}"
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


def _marginal_total(conn, table: str, col: "CategoricalColumn") -> int:
    """Total occurrences that the marginal counts sum to — the right denominator
    for percentages. For scalar columns that's the row count (NULLs included);
    for list columns it's the number of UNNESTed elements, which exceeds the row
    count when rows hold multivalued arrays.
    """
    if col.is_list:
        src = f'(SELECT UNNEST("{col.name}") AS v FROM {table})'
    else:
        src = f'(SELECT "{col.name}" AS v FROM {table})'
    return conn.execute(f"SELECT COUNT(*) FROM {src}").fetchone()[0]


def profile_table(
    conn,
    table: str,
    sv=None,
    *,
    top_n: int = 10,
    max_distinct: int = 50,
    max_ratio: float = 0.01,
    max_distinct_ceiling: int = 1000,
    columns: list[str] | None = None,
):
    """Profile one table: row count + per-categorical-column marginals.

    `columns`, if given, overrides auto-detection (intersected with the table's
    actual columns; cardinality is still measured for display).
    """
    from koza.model.graph_operations import ColumnProfile, TableProfile

    row_count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    if columns is not None:
        present = {c[0]: c[1] for c in _describe(conn, table)}
        cats: list[CategoricalColumn] = []
        for name in columns:
            if name not in present:
                logger.warning(f"Column '{name}' not in {table}, skipping")
                continue
            is_list = present[name].upper().endswith("[]")
            if is_list:
                n = conn.execute(
                    f'SELECT approx_count_distinct(x) FROM (SELECT UNNEST("{name}") AS x FROM {table})'
                ).fetchone()[0]
            else:
                n = conn.execute(f'SELECT approx_count_distinct("{name}") FROM {table}').fetchone()[0]
            cats.append(CategoricalColumn(name, n or 0, is_list, "override"))
    else:
        cats = detect_categorical_columns(
            conn, table, sv,
            max_distinct=max_distinct,
            max_ratio=max_ratio,
            max_distinct_ceiling=max_distinct_ceiling,
        )

    col_profiles = [
        ColumnProfile(
            column=c.name,
            distinct_count=c.distinct_count,
            reason=c.reason,
            is_list=c.is_list,
            top_values=_marginal(conn, table, c, top_n),
            total_count=_marginal_total(conn, table, c),
        )
        for c in cats
    ]
    return TableProfile(table=table, row_count=row_count, columns=col_profiles)


def profile_graph(config):
    """Profile a koza DuckDB: per-table, per-column categorical marginals.

    Auto-detects tables and categorical columns unless overridden. Optionally
    writes a long-form (table, column, value, count) export.
    """
    import time

    from koza.graph_operations.graph_schema import load_biolink_schemaview
    from koza.graph_operations.utils import GraphDatabase
    from koza.model.graph_operations import ProfileResult

    start = time.time()
    try:
        sv = load_biolink_schemaview()
    except Exception as e:  # pragma: no cover - schema is optional
        logger.debug(f"Biolink schema unavailable, cardinality-only: {e}")
        sv = None

    with GraphDatabase(config.database_path, read_only=True) as db:
        conn = db.conn
        tables = config.tables or _auto_tables(conn)
        table_profiles = [
            profile_table(
                conn, t, sv,
                top_n=config.top_n,
                max_distinct=config.max_distinct,
                max_ratio=config.max_ratio,
                max_distinct_ceiling=config.max_distinct_ceiling,
                columns=config.columns,
            )
            for t in tables
        ]
        if config.output_file:
            _write_marginals(conn, table_profiles, config)

    return ProfileResult(
        database_path=config.database_path,
        tables=table_profiles,
        output_file=config.output_file,
        total_time_seconds=time.time() - start,
    )


def _write_marginals(conn, table_profiles, config) -> None:
    """Write full long-form marginals (table, column, value, count) to a file."""
    selects = []
    for tp in table_profiles:
        for cp in tp.columns:
            if cp.is_list:
                src = f'(SELECT UNNEST("{cp.column}") AS v FROM {tp.table})'
            else:
                src = f'(SELECT "{cp.column}" AS v FROM {tp.table})'
            selects.append(
                f"SELECT '{tp.table}' AS table_name, '{cp.column}' AS column_name, "
                f"CAST(v AS VARCHAR) AS value, COUNT(*) AS count FROM {src} GROUP BY 3"
            )
    if not selects:
        return
    union = "\nUNION ALL\n".join(selects)
    query = f"SELECT * FROM ({union}) ORDER BY table_name, column_name, count DESC"
    fmt = config.output_format.value
    out = str(config.output_file)
    if fmt == "parquet":
        copy_opts = "(FORMAT PARQUET)"
    elif fmt == "jsonl":
        copy_opts = "(FORMAT JSON)"
    else:
        copy_opts = "(FORMAT CSV, DELIMITER '\t', HEADER)"
    conn.execute(f"COPY ({query}) TO '{out}' {copy_opts}")


def render_profile(result) -> str:
    """Render a ProfileResult as a readable terminal summary."""
    lines: list[str] = [str(result.database_path), ""]
    for tp in result.tables:
        lines.append(f"{tp.table} — {tp.row_count:,} rows")
        if not tp.columns:
            lines.append("    (no categorical columns detected)")
            lines.append("")
            continue
        for cp in tp.columns:
            shown = len(cp.top_values)
            more = "" if cp.distinct_count <= shown else f" · showing top {shown} of {cp.distinct_count}"
            # List columns are UNNESTed, so percentages are of elements (which can
            # sum past the row count when rows carry multivalued arrays), not of rows.
            unit = " · % of elements" if cp.is_list else ""
            lines.append(f"  {cp.column} · {cp.distinct_count} distinct · {cp.reason}{more}{unit}")
            denom = (cp.total_count or tp.row_count) or 1
            for value, count in cp.top_values:
                pct = 100.0 * count / denom
                val = "∅ (null)" if value is None else value
                lines.append(f"      {pct:5.1f}%  {count:>12,}  {val}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
