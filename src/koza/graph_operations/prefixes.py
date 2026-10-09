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

import difflib
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
    (restricted to ``config.only`` when given; an ``--only`` prefix that
    appears nowhere in the graph is an error). Unknown prefixes are left
    untouched. Each change is recorded in the ``prefix_canonicalization_log``
    audit table (see :func:`_ensure_log_table`); no ``original_*`` columns are
    written. The rewrites, the audit rows and any deduplication run in a single
    transaction, so a failure leaves the database unchanged. A dry run does
    the same work and rolls it back, so its counts are exact.

    Only ``nodes`` and ``edges`` are rewritten. Any other table in the
    database (``closure``, ``denormalized_*``, ``mappings``, ...) keeps the
    old ids; a warning names those tables so they can be rebuilt.

    Collisions are defined relative to the rows rewritten in this run only:

    - a rewritten node row collides when another row has the same ``id``;
    - a rewritten edge row collides when another row is identical to it on
      every column except ``id``. Edges that differ in sources, qualifiers or
      anything else do not collide.

    The collision counts are the rows ``--deduplicate`` would remove. With
    ``config.deduplicate`` they are removed: the pre-existing row is kept and
    the rewritten one dropped; when only rewritten rows collide, one of them
    is kept (first by ``file_source``, then insertion order). Rows that
    already duplicated each other before the run are never touched. Removed
    rows are copied, with ``run_at``, into
    ``prefix_canonicalization_removed_nodes`` / ``..._removed_edges``.

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
            census = _prefix_census(db)
            if only is not None:
                _check_only(only, census)
            usages = _classify(census, canonical)
            repairs = {
                u.prefix: u.canonical_prefix
                for u in usages
                if u.status == PrefixStatus.ALTERNATE_CASING and (only is None or u.prefix.lower() in only)
            }
            if only is not None:
                matched = {v.lower() for v in repairs}
                for requested in sorted(only - matched):
                    _warn(
                        warnings, f"--only {requested!r}: already canonical everywhere in the graph, nothing to repair"
                    )

            if not repairs:
                message = f"No prefixes with alternate casing to repair against context {config.context!r}"
                summary = _summary(True, message, db, 0, start_time, warnings, errors)
                if not config.quiet:
                    print_operation_summary(summary)
                return CanonicalizeResult(
                    success=True,
                    repairs={},
                    final_stats=db.get_stats(),
                    total_time_seconds=time.time() - start_time,
                    summary=summary,
                    warnings=warnings,
                )

            other_tables = _other_tables(db)
            if other_tables:
                _warn(
                    warnings,
                    "Only nodes and edges are rewritten; these tables may still hold the old ids "
                    f"and should be rebuilt: {', '.join(other_tables)}",
                )

            run_at = datetime.now(timezone.utc).replace(tzinfo=None)
            log_params = (run_at, config.context)
            rewritten = {"nodes": 0, "subject": 0, "object": 0}
            removed = {"nodes": 0, "edges": 0}

            db.conn.execute("BEGIN TRANSACTION")
            try:
                _ensure_log_table(db)
                db.conn.execute("CREATE OR REPLACE TEMP TABLE _canon_touched (tbl VARCHAR, rid BIGINT)")
                db.conn.execute("CREATE OR REPLACE TEMP TABLE _canon_repairs (variant VARCHAR, canonical VARCHAR)")
                db.conn.executemany("INSERT INTO _canon_repairs VALUES (?, ?)", list(repairs.items()))
                rewritten["nodes"] = _rewrite_column(db, "nodes", nodes.id, log_params)
                rewritten["subject"] = _rewrite_column(db, "edges", edges.subject, log_params)
                rewritten["object"] = _rewrite_column(db, "edges", edges.object, log_params)

                _find_collisions(db)
                node_collisions, edge_collisions = (
                    db.conn.execute(f"SELECT COUNT(*) FROM _canon_doomed WHERE tbl = '{t}'").fetchone()[0]
                    for t in ("nodes", "edges")
                )
                if config.deduplicate:
                    removed["nodes"] = _remove_collisions(db, "nodes", log_params)
                    removed["edges"] = _remove_collisions(db, "edges", log_params)

                for temp in ("_canon_doomed", "_canon_touched", "_canon_repairs"):
                    db.conn.execute(f"DROP TABLE {temp}")
                db.conn.execute("ROLLBACK" if config.dry_run else "COMMIT")
            except Exception:
                # DuckDB may already have aborted the transaction; don't let a
                # failed ROLLBACK mask the original error.
                try:
                    db.conn.execute("ROLLBACK")
                except Exception as rollback_error:
                    logger.debug(f"ROLLBACK after canonicalize failure: {rollback_error}")
                raise

            if not config.deduplicate:
                _warn_collisions(warnings, node_collisions, edge_collisions)

            total = sum(rewritten.values())
            verb = "Dry run — would canonicalize" if config.dry_run else "Canonicalized"
            message = (
                f"{verb} {len(repairs)} prefixes "
                f"({', '.join(f'{v} → {t}' for v, t in sorted(repairs.items()))}); "
                f"{'would rewrite' if config.dry_run else 'rewrote'} {total:,} references"
            )
            if removed["nodes"] or removed["edges"]:
                message += (
                    f"; {'would remove' if config.dry_run else 'removed'} {removed['nodes']:,} node and "
                    f"{removed['edges']:,} edge rows that duplicated another row"
                )
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


#: Sidecar tables holding rows removed by ``--deduplicate`` (same columns plus run_at).
REMOVED_TABLES = {
    "nodes": "prefix_canonicalization_removed_nodes",
    "edges": "prefix_canonicalization_removed_edges",
}

# Tables koza maintains alongside nodes/edges that carry no graph ids to rebuild.
_NON_ID_TABLES = {"nodes", "edges", "file_schemas", _KOZA_SCHEMA_TABLE, LOG_TABLE, *REMOVED_TABLES.values()}


def _warn(warnings: list[str], message: str) -> None:
    warnings.append(message)
    logger.warning(message)


def _check_only(only: set[str], census: dict[str, dict[str, int]]) -> None:
    """Raise when an --only prefix appears nowhere in the graph (likely a typo)."""
    observed = {p.lower() for p in census}
    missing = sorted(only - observed)
    if not missing:
        return
    parts = []
    for prefix in missing:
        close = difflib.get_close_matches(prefix, sorted(observed), n=3)
        hint = f" (did you mean: {', '.join(close)}?)" if close else ""
        parts.append(f"{prefix!r}{hint}")
    raise ValueError(f"--only prefix not found in the graph: {'; '.join(parts)}")


def _table_columns(db: GraphDatabase, table: str) -> list[str]:
    """Column names of a main-schema table in order, or an empty list when it does not exist."""
    rows = db.conn.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = ? AND table_schema = 'main' AND table_catalog = current_database()
        ORDER BY ordinal_position
        """,
        [table],
    ).fetchall()
    return [row[0] for row in rows]


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
            ``subject`` or ``object``); for ``deduplicate``, what the rows
            matched on (``id`` for nodes, ``all columns except id`` for edges).
        old_prefix / new_prefix: the spelling before and after (``rewrite``
            only; NULL for ``deduplicate``).
        example_value: one affected value — an id as it was before the
            rewrite, or the id / subject of a removed row.
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


def _find_collisions(db: GraphDatabase) -> None:
    """
    Fill _canon_doomed (tbl, rid) with the rewritten rows that duplicate another row.

    Identity is ``id`` for nodes and every column except ``id`` for edges.
    Within each identity group: if any row was not rewritten in this run, every
    rewritten row is doomed (the pre-existing row wins); otherwise all
    rewritten rows but one are (first by ``file_source``, then insertion
    order). Rows not rewritten in this run are never doomed, so duplicates
    that predate the run are left alone.
    """
    db.conn.execute("CREATE OR REPLACE TEMP TABLE _canon_doomed (tbl VARCHAR, rid BIGINT)")
    for table in ("nodes", "edges"):
        columns = _table_columns(db, table)
        if table == "nodes":
            key = [nodes.id] if nodes.id in columns else []
            # Narrow to groups that contain a rewritten row before windowing.
            candidates = f"""
                SELECT t.rowid AS _canon_rid, t.* FROM nodes t
                WHERE t.{nodes.id} IN (
                    SELECT n.{nodes.id} FROM nodes n JOIN _canon_touched w ON w.tbl = 'nodes' AND n.rowid = w.rid
                )
            """
        else:
            key = [c for c in columns if c != "id"]
            spo = [edges.subject, edges.predicate, edges.object]
            if not set(spo) <= set(columns):
                key = []
            on = " AND ".join(f"t.{c} IS NOT DISTINCT FROM k.{c}" for c in spo)
            candidates = f"""
                SELECT t.rowid AS _canon_rid, t.* FROM edges t
                SEMI JOIN (
                    SELECT DISTINCT {", ".join(f"e.{c}" for c in spo)}
                    FROM edges e JOIN (SELECT DISTINCT rid FROM _canon_touched WHERE tbl = 'edges') w
                      ON e.rowid = w.rid
                ) k ON {on}
            """
        if not key:
            continue

        partition = ", ".join(f'c."{k}"' for k in key)
        order = 'c."file_source" NULLS LAST, c._canon_rid' if "file_source" in columns else "c._canon_rid"
        db.conn.execute(f"""
            INSERT INTO _canon_doomed
            SELECT '{table}', rid FROM (
                SELECT c._canon_rid AS rid,
                       w.rid IS NOT NULL AS touched,
                       COUNT(*) FILTER (WHERE w.rid IS NULL) OVER (PARTITION BY {partition}) AS untouched,
                       ROW_NUMBER() OVER (PARTITION BY {partition}, (w.rid IS NOT NULL) ORDER BY {order}) AS rn
                FROM ({candidates}) c
                LEFT JOIN (SELECT DISTINCT rid FROM _canon_touched WHERE tbl = '{table}') w ON c._canon_rid = w.rid
            )
            WHERE touched AND (untouched > 0 OR rn > 1)
        """)


def _remove_collisions(db: GraphDatabase, table: str, log_params: tuple) -> int:
    """
    Move the doomed rows of `table` into its removed-rows sidecar.

    Copies them (with ``run_at``) into ``REMOVED_TABLES[table]``, logs one
    ``deduplicate`` audit row, deletes them, and returns how many were removed.
    """
    removed = db.conn.execute(f"SELECT COUNT(*) FROM _canon_doomed WHERE tbl = '{table}'").fetchone()[0]
    if not removed:
        return 0

    sidecar = REMOVED_TABLES[table]
    doomed = f"FROM {table} WHERE rowid IN (SELECT rid FROM _canon_doomed WHERE tbl = '{table}')"
    if not _table_columns(db, sidecar):
        db.conn.execute(f"CREATE TABLE {sidecar} AS SELECT CAST(NULL AS TIMESTAMP) AS run_at, * FROM {table} LIMIT 0")
    else:
        # The graph may have gained columns since the sidecar was created.
        sidecar_cols = set(_table_columns(db, sidecar))
        for name, dtype in db.conn.execute(f"SELECT column_name, column_type FROM (DESCRIBE {table})").fetchall():
            if name not in sidecar_cols:
                db.conn.execute(f'ALTER TABLE {sidecar} ADD COLUMN "{name}" {dtype}')
    db.conn.execute(f"INSERT INTO {sidecar} BY NAME SELECT ?::TIMESTAMP AS run_at, * {doomed}", [log_params[0]])

    example_col = nodes.id if table == "nodes" else edges.subject
    column_name = nodes.id if table == "nodes" else "all columns except id"
    db.conn.execute(
        f"""
        INSERT INTO {LOG_TABLE}
        SELECT ?, ?, 'deduplicate', '{table}', '{column_name}', NULL, NULL, min({example_col}), COUNT(*) {doomed}
        """,
        list(log_params),
    )
    db.conn.execute(f"DELETE {doomed}")
    return removed


def _warn_collisions(warnings: list[str], node_collisions: int, edge_collisions: int) -> None:
    """Warn about rewritten rows that duplicate other nodes/edges (kept without --deduplicate)."""
    advice = (
        "They were kept. To remove them, run the repair itself with --deduplicate (preview with "
        "--dry-run --deduplicate); a later --deduplicate run cannot, since it only acts on rows "
        "rewritten in the same run."
    )
    if node_collisions:
        _warn(warnings, f"{node_collisions} rewritten node rows now share an id with another node row. {advice}")
    if edge_collisions:
        _warn(
            warnings,
            f"{edge_collisions} rewritten edge rows are now identical (apart from id) to another edge row. {advice}",
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
