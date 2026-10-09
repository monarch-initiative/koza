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

    Node collisions are defined relative to the rows rewritten in this run
    only: a rewritten node row collides when another row has the same ``id``.
    The collision count is the rows ``--deduplicate`` would remove. With
    ``config.deduplicate`` they are removed: the pre-existing row is kept and
    the rewritten one dropped; when only rewritten rows collide, one of them
    is kept (first by ``file_source``, then insertion order). Rows that
    already duplicated each other before the run are never touched. Removed
    rows are copied, with ``run_at``, into
    ``prefix_canonicalization_removed_nodes``. Edges are never deduplicated.

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
            nodes_removed = 0

            db.conn.execute("BEGIN TRANSACTION")
            try:
                _ensure_log_table(db)
                db.conn.execute("CREATE OR REPLACE TEMP TABLE _canon_touched (rid BIGINT)")
                db.conn.execute("CREATE OR REPLACE TEMP TABLE _canon_repairs (variant VARCHAR, canonical VARCHAR)")
                db.conn.executemany("INSERT INTO _canon_repairs VALUES (?, ?)", list(repairs.items()))
                rewritten["nodes"] = _rewrite_column(db, "nodes", nodes.id, log_params)
                rewritten["subject"] = _rewrite_column(db, "edges", edges.subject, log_params)
                rewritten["object"] = _rewrite_column(db, "edges", edges.object, log_params)

                node_collisions = _find_node_collisions(db)
                if config.deduplicate:
                    nodes_removed = _remove_node_collisions(db, log_params)

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
                _warn_collisions(warnings, node_collisions)

            total = sum(rewritten.values())
            verb = "Dry run — would canonicalize" if config.dry_run else "Canonicalized"
            message = (
                f"{verb} {len(repairs)} prefixes "
                f"({', '.join(f'{v} → {t}' for v, t in sorted(repairs.items()))}); "
                f"{'would rewrite' if config.dry_run else 'rewrote'} {total:,} references"
            )
            if nodes_removed:
                message += (
                    f"; {'would remove' if config.dry_run else 'removed'} {nodes_removed:,} node rows "
                    f"that duplicated an existing node id"
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
                nodes_removed=nodes_removed,
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


#: Sidecar table holding node rows removed by ``--deduplicate`` (same columns plus run_at).
REMOVED_NODES_TABLE = "prefix_canonicalization_removed_nodes"

# Tables koza maintains alongside nodes/edges that carry no graph ids to rebuild.
_NON_ID_TABLES = {"nodes", "edges", "file_schemas", _KOZA_SCHEMA_TABLE, LOG_TABLE, REMOVED_NODES_TABLE}


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
        table_name: ``nodes`` or ``edges`` (``deduplicate`` rows are
            always ``nodes``).
        column_name: the column rewritten (``id``, ``subject`` or
            ``object``), or ``id`` for ``deduplicate``.
        old_prefix / new_prefix: the spelling before and after (``rewrite``
            only; NULL for ``deduplicate``).
        example_value: one affected value — an id as it was before the
            rewrite, or the id of a removed node row.
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

    Logs one audit row per repaired prefix and, for nodes, marks the
    rewritten rows in _canon_touched. Returns rows changed.
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
    if table == "nodes":
        db.conn.execute(f"INSERT INTO _canon_touched SELECT t.rowid FROM nodes t JOIN _canon_repairs r ON {match}")
    result = db.conn.execute(f"""
        UPDATE {table}
        SET {column} = r.canonical || substr({column}, length(r.variant) + 1)
        FROM _canon_repairs r
        WHERE split_part({table}.{column}, ':', 1) = r.variant
    """).fetchone()
    return result[0] if result else 0


def _find_node_collisions(db: GraphDatabase) -> int:
    """
    Fill _canon_doomed (rid) with rewritten node rows that share an id with another row.

    Within each id: if any row was not rewritten in this run, every rewritten
    row is doomed (the pre-existing row wins); otherwise all rewritten rows
    but one are (first by ``file_source``, then insertion order). Rows not
    rewritten in this run are never doomed, so duplicates that predate the
    run are left alone. Returns the number of doomed rows.
    """
    db.conn.execute("CREATE OR REPLACE TEMP TABLE _canon_doomed (rid BIGINT)")
    columns = _table_columns(db, "nodes")
    if nodes.id not in columns:
        return 0

    order = "n.file_source NULLS LAST, n.rowid" if "file_source" in columns else "n.rowid"
    db.conn.execute(f"""
        INSERT INTO _canon_doomed
        SELECT rid FROM (
            SELECT n.rowid AS rid,
                   w.rid IS NOT NULL AS touched,
                   COUNT(*) FILTER (WHERE w.rid IS NULL) OVER (PARTITION BY n.{nodes.id}) AS untouched,
                   ROW_NUMBER() OVER (PARTITION BY n.{nodes.id}, (w.rid IS NOT NULL) ORDER BY {order}) AS rn
            FROM nodes n
            LEFT JOIN _canon_touched w ON n.rowid = w.rid
            -- only ids that a rewritten row now carries
            WHERE n.{nodes.id} IN (SELECT t.{nodes.id} FROM nodes t JOIN _canon_touched x ON t.rowid = x.rid)
        )
        WHERE touched AND (untouched > 0 OR rn > 1)
    """)
    return db.conn.execute("SELECT COUNT(*) FROM _canon_doomed").fetchone()[0]


def _remove_node_collisions(db: GraphDatabase, log_params: tuple) -> int:
    """
    Move the doomed node rows into the removed-nodes sidecar.

    Copies them (with ``run_at``) into ``REMOVED_NODES_TABLE``, logs one
    ``deduplicate`` audit row, deletes them, and returns how many were removed.
    """
    removed = db.conn.execute("SELECT COUNT(*) FROM _canon_doomed").fetchone()[0]
    if not removed:
        return 0

    doomed = "FROM nodes WHERE rowid IN (SELECT rid FROM _canon_doomed)"
    if not _table_columns(db, REMOVED_NODES_TABLE):
        db.conn.execute(
            f"CREATE TABLE {REMOVED_NODES_TABLE} AS SELECT CAST(NULL AS TIMESTAMP) AS run_at, * FROM nodes LIMIT 0"
        )
    else:
        # The graph may have gained columns since the sidecar was created.
        sidecar_cols = set(_table_columns(db, REMOVED_NODES_TABLE))
        for name, dtype in db.conn.execute("SELECT column_name, column_type FROM (DESCRIBE nodes)").fetchall():
            if name not in sidecar_cols:
                db.conn.execute(f'ALTER TABLE {REMOVED_NODES_TABLE} ADD COLUMN "{name}" {dtype}')
    db.conn.execute(
        f"INSERT INTO {REMOVED_NODES_TABLE} BY NAME SELECT ?::TIMESTAMP AS run_at, * {doomed}", [log_params[0]]
    )
    db.conn.execute(
        f"""
        INSERT INTO {LOG_TABLE}
        SELECT ?, ?, 'deduplicate', 'nodes', '{nodes.id}', NULL, NULL, min({nodes.id}), COUNT(*) {doomed}
        """,
        list(log_params),
    )
    db.conn.execute(f"DELETE {doomed}")
    return removed


def _warn_collisions(warnings: list[str], node_collisions: int) -> None:
    """Warn about rewritten node rows that share an id with another row (kept without --deduplicate)."""
    if node_collisions:
        _warn(
            warnings,
            f"{node_collisions} rewritten node rows now share an id with another node row. They were kept. "
            "To remove them, run the repair itself with --deduplicate (preview with --dry-run --deduplicate); "
            "a later --deduplicate run cannot, since it only acts on rows rewritten in the same run.",
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
