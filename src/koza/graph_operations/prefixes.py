"""
Prefix census and canonicalization against a prefixmaps context.

Two graphs that spell the same prefix differently (``hgnc:746`` vs
``HGNC:746``) join without error and land as disjoint node sets. The
operations here make that visible and repairable:

- :func:`generate_prefix_report` — census every prefix appearing in
  ``nodes.id``, ``edges.subject`` and ``edges.object``, classified against a
  `prefixmaps <https://github.com/linkml/prefixmaps>`_ context as
  ``canonical`` (exact match), ``alternate_casing`` (matches a context prefix
  case-insensitively but not exactly), or ``unknown`` (absent from the
  context).
- :func:`canonicalize_graph` — rewrite alternately-cased prefixes to their
  canonical spelling, recording each change in the
  ``prefix_canonicalization_log`` audit table.

Canonicalization deliberately repairs **alternate casing only**. Mapping one
known prefix to a different one is an identifier-level decision and belongs
to ``koza normalize`` (SSSOM); an ``unknown`` prefix is reported, never
touched. Canonicalize does not write ``original_*`` columns: those belong to
``normalize``. Note ``prefixmaps.load_converter(...).standardize_curie`` does
not treat alternately-cased prefixes as synonyms (``hgnc:746`` → ``None``),
which is why this module builds its own case-insensitive lookup over the
context's prefixes.
"""

import time
from collections import defaultdict
from datetime import datetime, timezone

from loguru import logger

from koza.model.graph_operations import (
    CanonicalizeConfig,
    CanonicalizeResult,
    OperationSummary,
    PrefixReport,
    PrefixReportConfig,
    PrefixReportResult,
    PrefixStatus,
    PrefixUsage,
)

from .graph_schema import _KOZA_SCHEMA_TABLE
from .slots import edges, nodes
from .utils import GraphDatabase, print_operation_summary

#: Audit table canonicalize appends to; one row per distinct change per run.
LOG_TABLE = "prefix_canonicalization_log"

# (table, column, PrefixUsage attribute) triples the census walks.
_CENSUS_COLUMNS = (
    ("nodes", nodes.id, "node_ids"),
    ("edges", edges.subject, "edge_subjects"),
    ("edges", edges.object, "edge_objects"),
)


def load_canonical_prefixes(context: str = "merged") -> dict[str, str]:
    """
    Build a case-insensitive lookup of canonical prefixes from a prefixmaps context.

    Args:
        context: Name of the prefixmaps context to load (e.g. "merged",
            "bioregistry.upper", "obo").

    Returns:
        Mapping of lowercased prefix -> canonical prefix spelling. When two
        canonical prefixes in the context collide case-insensitively (rare),
        the lexicographically smallest is kept and a warning is logged.
    """
    from prefixmaps import load_context

    ctx = load_context(context)
    lookup: dict[str, str] = {}
    for prefix in sorted(ctx.as_dict()):
        key = prefix.lower()
        if key in lookup and lookup[key] != prefix:
            logger.warning(
                f"Context {context!r} has case-colliding prefixes "
                f"{lookup[key]!r} and {prefix!r}; keeping {lookup[key]!r}"
            )
            continue
        lookup[key] = prefix
    return lookup


def _prefix_census(db: GraphDatabase) -> dict[str, dict[str, int]]:
    """Count CURIE prefixes per column. Returns {prefix: {usage_attr: count}}."""
    existing = {
        row[0]
        for row in db.conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_name IN ('nodes', 'edges')"
        ).fetchall()
    }
    census: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for table, column, attr in _CENSUS_COLUMNS:
        if table not in existing:
            continue
        rows = db.conn.execute(f"""
            SELECT split_part({column}, ':', 1) AS prefix, COUNT(*)
            FROM {table}
            WHERE {column} IS NOT NULL AND {column} LIKE '%:%'
            GROUP BY 1
        """).fetchall()
        for prefix, count in rows:
            census[prefix][attr] += count
    return census


def _classify(census: dict[str, dict[str, int]], canonical: dict[str, str]) -> list[PrefixUsage]:
    """Classify each observed prefix against the canonical lookup."""
    usages = []
    for prefix in sorted(census):
        counts = census[prefix]
        target = canonical.get(prefix.lower())
        if target == prefix:
            status, suggestion = PrefixStatus.CANONICAL, None
        elif target is not None:
            status, suggestion = PrefixStatus.ALTERNATE_CASING, target
        else:
            status, suggestion = PrefixStatus.UNKNOWN, None
        usages.append(
            PrefixUsage(
                prefix=prefix,
                status=status,
                canonical_prefix=suggestion,
                node_ids=counts.get("node_ids", 0),
                edge_subjects=counts.get("edge_subjects", 0),
                edge_objects=counts.get("edge_objects", 0),
            )
        )
    return usages


def generate_prefix_report(config: PrefixReportConfig) -> PrefixReportResult:
    """
    Census the prefixes used in a graph database against a prefixmaps context.

    Args:
        config: PrefixReportConfig with database_path, context, output_file, quiet.

    Returns:
        PrefixReportResult with the classified census (and the YAML output
        path when one was written).
    """
    start_time = time.time()
    canonical = load_canonical_prefixes(config.context)

    with GraphDatabase(config.database_path, read_only=True) as db:
        usages = _classify(_prefix_census(db), canonical)

    report = PrefixReport(
        context=config.context,
        total_prefixes=len(usages),
        canonical=sum(1 for u in usages if u.status == PrefixStatus.CANONICAL),
        alternate_casing=sum(1 for u in usages if u.status == PrefixStatus.ALTERNATE_CASING),
        unknown=sum(1 for u in usages if u.status == PrefixStatus.UNKNOWN),
        prefixes=usages,
    )

    output_file = None
    if config.output_file:
        import yaml

        config.output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config.output_file, "w") as f:
            yaml.dump(report.model_dump(mode="json"), f, default_flow_style=False, sort_keys=False)
        output_file = config.output_file

    if not config.quiet:
        print(
            f"Prefixes in graph: {report.total_prefixes} "
            f"({report.canonical} canonical, {report.alternate_casing} with alternate casing, "
            f"{report.unknown} unknown to context {config.context!r})"
        )
        for usage in usages:
            if usage.status == PrefixStatus.ALTERNATE_CASING:
                total = usage.node_ids + usage.edge_subjects + usage.edge_objects
                print(f"  ⚠️  {usage.prefix} → {usage.canonical_prefix} ({total:,} references)")

    return PrefixReportResult(
        prefix_report=report,
        output_file=output_file,
        total_time_seconds=time.time() - start_time,
    )


def canonicalize_graph(config: CanonicalizeConfig) -> CanonicalizeResult:
    """
    Rewrite alternately-cased prefixes to their canonical spelling.

    Repairs ``nodes.id``, ``edges.subject`` and ``edges.object`` for every
    prefix that matches a canonical prefix case-insensitively but not exactly
    (restricted to ``config.only`` when given). Unknown prefixes are left
    untouched. Each change is recorded in the ``prefix_canonicalization_log``
    audit table (see :func:`_ensure_log_table`); no ``original_*`` columns are
    written. The rewrites, the audit rows and any deduplication run in a single
    transaction, so a failure leaves the database unchanged.

    Only ``nodes`` and ``edges`` are rewritten. Any other table in the
    database (``closure``, ``denormalized_*``, ``mappings``, ...) keeps the
    old ids; a warning names those tables so they can be rebuilt.

    A rewrite can land a repaired node id on an id the graph already has
    (``hgnc:746`` arriving at an existing ``HGNC:746`` row), or make two
    edges share the same subject/predicate/object. Those collisions are
    counted and warned about. With ``config.deduplicate`` they are removed:
    within each colliding group one row is kept, preferring a row that was
    not rewritten, then the first by ``file_source``, then insertion order.

    On a run with nothing left to rewrite, collisions are looked for among ids
    whose prefix an earlier run canonicalized (per the audit table), so a
    re-run reports them and ``--deduplicate`` can still remove them.

    Args:
        config: CanonicalizeConfig with database_path, context, only,
            deduplicate, dry_run, quiet.

    Returns:
        CanonicalizeResult with the applied repairs, rewrite counts,
        collision counts and rows removed.
    """
    start_time = time.time()
    errors: list[str] = []
    warnings: list[str] = []

    try:
        canonical = load_canonical_prefixes(config.context)
        only = {p.lower() for p in config.only} if config.only else None

        with GraphDatabase(config.database_path) as db:
            usages = _classify(_prefix_census(db), canonical)
            repairs = {
                u.prefix: u.canonical_prefix
                for u in usages
                if u.status == PrefixStatus.ALTERNATE_CASING and (only is None or u.prefix.lower() in only)
            }
            if only is not None:
                matched = {v.lower() for v in repairs}
                for requested in sorted(only - matched):
                    _warn(warnings, f"--only {requested!r}: no alternately-cased spelling of this prefix in the graph")

            if repairs:
                other_tables = _other_tables(db)
                if other_tables:
                    _warn(
                        warnings,
                        "Only nodes and edges are rewritten; these tables may still hold the old ids "
                        f"and should be rebuilt: {', '.join(other_tables)}",
                    )

            if config.dry_run:
                message = (
                    "Dry run — would repair: "
                    + ", ".join(f"{variant} → {target}" for variant, target in sorted(repairs.items()))
                    if repairs
                    else f"Dry run — no prefixes with alternate casing to repair against context {config.context!r}"
                )
                summary = _summary(True, message, db, 0, start_time, warnings, errors)
                if not config.quiet:
                    print_operation_summary(summary)
                return CanonicalizeResult(
                    success=True,
                    repairs=repairs,
                    final_stats=db.get_stats(),
                    total_time_seconds=time.time() - start_time,
                    summary=summary,
                    warnings=warnings,
                )

            run_at = datetime.now(timezone.utc).replace(tzinfo=None)
            rewritten = {"nodes": 0, "subject": 0, "object": 0}
            removed = {"nodes": 0, "edges": 0}

            db.conn.execute("BEGIN TRANSACTION")
            try:
                db.conn.execute("CREATE OR REPLACE TEMP TABLE _canon_touched (tbl VARCHAR, rid BIGINT)")
                if repairs:
                    _ensure_log_table(db)
                    db.conn.execute("CREATE OR REPLACE TEMP TABLE _canon_repairs (variant VARCHAR, canonical VARCHAR)")
                    db.conn.executemany("INSERT INTO _canon_repairs VALUES (?, ?)", list(repairs.items()))
                    log_params = (run_at, config.context)
                    rewritten["nodes"] = _rewrite_column(db, "nodes", nodes.id, log_params)
                    rewritten["subject"] = _rewrite_column(db, "edges", edges.subject, log_params)
                    rewritten["object"] = _rewrite_column(db, "edges", edges.object, log_params)
                    db.conn.execute("DROP TABLE _canon_repairs")
                else:
                    _mark_touched_from_log(db)

                node_collisions, edge_collisions = _count_collisions(db)
                if config.deduplicate and (node_collisions or edge_collisions):
                    _ensure_log_table(db)
                    removed["nodes"] = _deduplicate(db, "nodes", [nodes.id], (run_at, config.context))
                    removed["edges"] = _deduplicate(
                        db, "edges", [edges.subject, edges.predicate, edges.object], (run_at, config.context)
                    )

                db.conn.execute("DROP TABLE _canon_touched")
                db.conn.execute("COMMIT")
            except Exception:
                # DuckDB may already have aborted the transaction; don't let a
                # failed ROLLBACK mask the original error.
                try:
                    db.conn.execute("ROLLBACK")
                except Exception as rollback_error:
                    logger.debug(f"ROLLBACK after canonicalize failure: {rollback_error}")
                raise

            if config.deduplicate:
                if removed["nodes"] or removed["edges"]:
                    logger.info(
                        f"Removed {removed['nodes']:,} colliding node rows and {removed['edges']:,} colliding edge rows"
                    )
            else:
                _warn_collisions(warnings, node_collisions, edge_collisions)

            total = sum(rewritten.values())
            if repairs:
                message = (
                    f"Canonicalized {len(repairs)} prefixes "
                    f"({', '.join(f'{v} → {t}' for v, t in sorted(repairs.items()))}); "
                    f"rewrote {total:,} references"
                )
            else:
                message = f"No prefixes with alternate casing to repair against context {config.context!r}"
            if removed["nodes"] or removed["edges"]:
                message += f"; removed {removed['nodes']:,} node and {removed['edges']:,} edge rows that collided"
            summary = _summary(True, message, db, total, start_time, warnings, errors)
            if not config.quiet:
                print_operation_summary(summary)

            return CanonicalizeResult(
                success=True,
                repairs=repairs,
                node_ids_rewritten=rewritten["nodes"],
                edge_subjects_rewritten=rewritten["subject"],
                edge_objects_rewritten=rewritten["object"],
                node_id_collisions=node_collisions,
                edge_collisions=edge_collisions,
                nodes_removed=removed["nodes"],
                edges_removed=removed["edges"],
                final_stats=db.get_stats(),
                total_time_seconds=time.time() - start_time,
                summary=summary,
                warnings=warnings,
            )

    except Exception as e:
        error_msg = f"Canonicalize operation failed: {e}"
        errors.append(error_msg)
        logger.error(error_msg)
        summary = OperationSummary(
            operation="canonicalize",
            success=False,
            message=error_msg,
            stats=None,
            files_processed=0,
            total_time_seconds=time.time() - start_time,
            warnings=warnings,
            errors=errors,
        )
        if not config.quiet:
            print_operation_summary(summary)
        return CanonicalizeResult(
            success=False,
            total_time_seconds=time.time() - start_time,
            summary=summary,
            errors=errors,
            warnings=warnings,
        )


# Tables koza maintains alongside nodes/edges that carry no graph ids.
_NON_ID_TABLES = {"nodes", "edges", "file_schemas", _KOZA_SCHEMA_TABLE, LOG_TABLE}


def _warn(warnings: list[str], message: str) -> None:
    warnings.append(message)
    logger.warning(message)


def _table_columns(db: GraphDatabase, table: str) -> set[str]:
    """Column names of a main-schema table, or an empty set when it does not exist."""
    rows = db.conn.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = ? AND table_schema = 'main' AND table_catalog = current_database()
        """,
        [table],
    ).fetchall()
    return {row[0] for row in rows}


def _other_tables(db: GraphDatabase) -> list[str]:
    """Tables/views besides nodes and edges (closure, denormalized_*, mappings, ...)."""
    rows = db.conn.execute(
        """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'main' AND table_catalog = current_database()
        ORDER BY table_name
        """
    ).fetchall()
    return [row[0] for row in rows if row[0] not in _NON_ID_TABLES]


def _ensure_log_table(db: GraphDatabase) -> None:
    """
    Create the audit table if needed. Canonicalize only ever appends to it.

    Columns:
        run_at: UTC timestamp shared by every row a single run writes.
        context: prefixmaps context the run canonicalized against.
        action: ``rewrite`` (a prefix was respelled) or ``deduplicate``
            (colliding rows were removed).
        table_name: ``nodes`` or ``edges``.
        column_name: for ``rewrite``, the column rewritten (``id``,
            ``subject`` or ``object``); for ``deduplicate``, the key the
            collision was on (``id`` or ``subject,predicate,object``).
        old_prefix / new_prefix: the spelling before and after (``rewrite``
            only; NULL for ``deduplicate``).
        example_value: one affected value — an id as it was before the
            rewrite, or the key of a group that lost rows.
        row_count: rows rewritten, or rows removed.
    """
    db.conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {LOG_TABLE} (
            run_at TIMESTAMP,
            context VARCHAR,
            action VARCHAR,
            table_name VARCHAR,
            column_name VARCHAR,
            old_prefix VARCHAR,
            new_prefix VARCHAR,
            example_value VARCHAR,
            row_count BIGINT
        )
    """)


def _rewrite_column(db: GraphDatabase, table: str, column: str, log_params: tuple) -> int:
    """
    Rewrite one CURIE column via the _canon_repairs temp table.

    Logs one audit row per repaired prefix and marks the rewritten rows in
    _canon_touched. Returns rows changed.
    """
    if column not in _table_columns(db, table):
        return 0

    match = f"split_part(t.{column}, ':', 1) = r.variant"
    db.conn.execute(
        f"""
        INSERT INTO {LOG_TABLE}
        SELECT ?, ?, 'rewrite', '{table}', '{column}', r.variant, r.canonical, min(t.{column}), COUNT(*)
        FROM {table} t JOIN _canon_repairs r ON {match}
        GROUP BY r.variant, r.canonical
        """,
        list(log_params),
    )
    db.conn.execute(f"""
        INSERT INTO _canon_touched
        SELECT '{table}', t.rowid FROM {table} t JOIN _canon_repairs r ON {match}
    """)
    result = db.conn.execute(f"""
        UPDATE {table}
        SET {column} = r.canonical || substr({column}, length(r.variant) + 1)
        FROM _canon_repairs r
        WHERE split_part({table}.{column}, ':', 1) = r.variant
    """).fetchone()
    return result[0] if result else 0


def _mark_touched_from_log(db: GraphDatabase) -> None:
    """
    Mark rows whose prefix an earlier run canonicalized (per the audit table).

    Used on runs with nothing left to rewrite, so collisions from an earlier
    run are still reported and can still be deduplicated.
    """
    if not _table_columns(db, LOG_TABLE):
        return
    for table, column in (("nodes", nodes.id), ("edges", edges.subject), ("edges", edges.object)):
        if column not in _table_columns(db, table):
            continue
        db.conn.execute(
            f"""
            INSERT INTO _canon_touched
            SELECT '{table}', t.rowid FROM {table} t
            WHERE split_part(t.{column}, ':', 1) IN (
                SELECT new_prefix FROM {LOG_TABLE}
                WHERE action = 'rewrite' AND table_name = ? AND column_name = ?
            )
            """,
            [table, column],
        )


def _collision_groups_sql(table: str, key: list[str]) -> str:
    """SQL selecting the key of every duplicate group in `table` that contains a touched row."""
    key_cols = ", ".join(f"t.{k}" for k in key)
    return f"""
        SELECT {key_cols}
        FROM {table} t
        LEFT JOIN (SELECT DISTINCT rid FROM _canon_touched WHERE tbl = '{table}') w ON t.rowid = w.rid
        GROUP BY {key_cols}
        HAVING COUNT(*) > 1 AND COUNT(w.rid) > 0
    """


def _count_collisions(db: GraphDatabase) -> tuple[int, int]:
    """
    Count duplicate groups that involve a touched row (see _canon_touched).

    Returns (node ids shared by more than one node row, subject/predicate/object
    triples shared by more than one edge row). Missing tables or key columns
    contribute 0.
    """
    counts = []
    for table, key in (("nodes", [nodes.id]), ("edges", [edges.subject, edges.predicate, edges.object])):
        if not set(key) <= _table_columns(db, table):
            counts.append(0)
            continue
        counts.append(db.conn.execute(f"SELECT COUNT(*) FROM ({_collision_groups_sql(table, key)})").fetchone()[0])
    return counts[0], counts[1]


def _deduplicate(db: GraphDatabase, table: str, key: list[str], log_params: tuple) -> int:
    """
    Remove all but one row from each duplicate group that involves a touched row.

    Keeps a row that was not touched (i.e. the pre-existing canonical row)
    when there is one, then the first by ``file_source`` (the same tie-break
    koza's id-based deduplication uses), then insertion order. Logs one
    ``deduplicate`` audit row and returns rows removed.
    """
    columns = _table_columns(db, table)
    if not set(key) <= columns:
        return 0

    on = " AND ".join(f"t.{k} IS NOT DISTINCT FROM g.{k}" for k in key)
    partition = ", ".join(f"t.{k}" for k in key)
    order = ["(w.rid IS NOT NULL)"]
    if "file_source" in columns:
        order.append("t.file_source NULLS LAST")
    order.append("t.rowid")
    example_key = " || ',' || ".join(f"coalesce(g.{k}, '')" for k in key)

    db.conn.execute(f"""
        CREATE OR REPLACE TEMP TABLE _canon_doomed AS
        SELECT rid, example FROM (
            SELECT t.rowid AS rid, {example_key} AS example,
                   ROW_NUMBER() OVER (PARTITION BY {partition} ORDER BY {", ".join(order)}) AS rn
            FROM {table} t
            JOIN ({_collision_groups_sql(table, key)}) g ON {on}
            LEFT JOIN (SELECT DISTINCT rid FROM _canon_touched WHERE tbl = '{table}') w ON t.rowid = w.rid
        ) WHERE rn > 1
    """)
    removed = db.conn.execute("SELECT COUNT(*) FROM _canon_doomed").fetchone()[0]
    if removed:
        db.conn.execute(
            f"""
            INSERT INTO {LOG_TABLE}
            SELECT ?, ?, 'deduplicate', '{table}', '{",".join(key)}', NULL, NULL, min(example), COUNT(*)
            FROM _canon_doomed
            """,
            list(log_params),
        )
        db.conn.execute(f"DELETE FROM {table} WHERE rowid IN (SELECT rid FROM _canon_doomed)")
    db.conn.execute("DROP TABLE _canon_doomed")
    return removed


def _warn_collisions(warnings: list[str], node_collisions: int, edge_collisions: int) -> None:
    """Warn about canonicalized ids that duplicate other nodes/edges."""
    if node_collisions:
        _warn(
            warnings,
            f"{node_collisions} canonicalized node ids are shared by more than one row "
            f"(a repaired id landed on an existing one). The rows were kept; "
            f"run `koza canonicalize --deduplicate` to remove the extras.",
        )
    if edge_collisions:
        _warn(
            warnings,
            f"{edge_collisions} subject/predicate/object triples involving canonicalized ids are "
            f"shared by more than one edge. The rows were kept; run `koza canonicalize --deduplicate` "
            f"to remove the extras.",
        )


def _summary(
    success: bool,
    message: str,
    db: GraphDatabase,
    references_rewritten: int,
    start_time: float,
    warnings: list[str],
    errors: list[str],
) -> OperationSummary:
    """Build the OperationSummary for a canonicalize run."""
    return OperationSummary(
        operation="canonicalize",
        success=success,
        message=message,
        stats=db.get_stats(),
        files_processed=0,
        total_time_seconds=time.time() - start_time,
        warnings=warnings,
        errors=errors,
    )
