"""
Prefix census and canonicalization against a prefixmaps context.

Two graphs that spell the same prefix differently (``hgnc:746`` vs
``HGNC:746``) join without error and land as disjoint node sets. The
operations here make that visible and repairable:

- :func:`generate_prefix_report` — census every prefix appearing in
  ``nodes.id``, ``edges.subject`` and ``edges.object``, classified against a
  `prefixmaps <https://github.com/linkml/prefixmaps>`_ context as
  ``canonical`` (exact match), ``case_variant`` (matches a context prefix
  case-insensitively but not exactly), or ``unknown`` (absent from the
  context).
- :func:`canonicalize_graph` — rewrite the case-variant prefixes to their
  canonical spelling, preserving originals in ``original_id`` (nodes) and
  ``original_subject``/``original_object`` (edges, the same slots
  ``normalize`` uses).

Canonicalization deliberately repairs **case variants only**. Mapping one
known prefix to a different one is an identifier-level decision and belongs
to ``koza normalize`` (SSSOM); an ``unknown`` prefix is reported, never
touched. Note ``prefixmaps.load_converter(...).standardize_curie`` does not
treat case variants as synonyms (``hgnc:746`` → ``None``), which is why this
module builds its own case-insensitive lookup over the context's prefixes.
"""

import time
from collections import defaultdict

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

from .graph_schema import _KOZA_SCHEMA_TABLE, ensure_slots
from .slots import edges, nodes
from .utils import GraphDatabase, print_operation_summary

DECLARED_OUTPUTS: dict[str, dict[str, dict]] = {
    "Entity": {
        "original_id": {
            "description": "Node ID before prefix canonicalization.",
            "range": "string",
            "multivalued": False,
        },
    },
    "Association": {
        "original_subject": {
            "description": "Subject ID before normalization or canonicalization.",
            "range": "string",
            "multivalued": False,
        },
        "original_object": {
            "description": "Object ID before normalization or canonicalization.",
            "range": "string",
            "multivalued": False,
        },
    },
}

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
            status, suggestion = PrefixStatus.CASE_VARIANT, target
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
        case_variants=sum(1 for u in usages if u.status == PrefixStatus.CASE_VARIANT),
        unknown=sum(1 for u in usages if u.status == PrefixStatus.UNKNOWN),
        prefixes=usages,
    )

    output_file = None
    if config.output_file:
        import yaml

        config.output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config.output_file, "w") as f:
            yaml.dump(report.model_dump(), f, default_flow_style=False, sort_keys=False)
        output_file = config.output_file

    if not config.quiet:
        print(
            f"Prefixes in graph: {report.total_prefixes} "
            f"({report.canonical} canonical, {report.case_variants} case variants, "
            f"{report.unknown} unknown to context {config.context!r})"
        )
        for usage in usages:
            if usage.status == PrefixStatus.CASE_VARIANT:
                total = usage.node_ids + usage.edge_subjects + usage.edge_objects
                print(f"  ⚠️  {usage.prefix} → {usage.canonical_prefix} ({total:,} references)")

    return PrefixReportResult(
        prefix_report=report,
        output_file=output_file,
        total_time_seconds=time.time() - start_time,
    )


def canonicalize_graph(config: CanonicalizeConfig) -> CanonicalizeResult:
    """
    Rewrite case-variant prefixes to their canonical spelling.

    Repairs ``nodes.id``, ``edges.subject`` and ``edges.object`` for every
    prefix that matches a canonical prefix case-insensitively but not exactly
    (restricted to ``config.only`` when given). Original identifiers are
    preserved in ``original_id`` / ``original_subject`` / ``original_object``
    (existing values in those columns are never overwritten). Unknown
    prefixes are left untouched. All rewrites run in a single transaction, so
    a failure leaves the database unchanged.

    Only ``nodes`` and ``edges`` are rewritten. Any other table in the
    database (``closure``, ``denormalized_*``, ``mappings``, ...) keeps the
    old ids; a warning names those tables so they can be rebuilt.

    A rewrite can land a repaired node id on an id the graph already has
    (``hgnc:746`` arriving at an existing ``HGNC:746`` row), or make two
    edges share the same subject/predicate/object. Those collisions are
    counted and reported as warnings (on every run, including re-runs that
    find nothing left to repair); they are not merged.

    Args:
        config: CanonicalizeConfig with database_path, context, only, dry_run, quiet.

    Returns:
        CanonicalizeResult with the applied repairs and rewrite counts.
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
                if u.status == PrefixStatus.CASE_VARIANT and (only is None or u.prefix.lower() in only)
            }
            if only is not None:
                matched = {v.lower() for v in repairs}
                for requested in sorted(only - matched):
                    _warn(warnings, f"--only {requested!r}: no case-variant spelling of this prefix in the graph")

            if not repairs:
                # Collisions left by an earlier run are still worth surfacing.
                node_collisions, edge_collisions = _count_collisions(db)
                _warn_collisions(warnings, node_collisions, edge_collisions)
                message = f"No case-variant prefixes to repair against context {config.context!r}"
                summary = _summary(True, message, db, 0, start_time, warnings, errors)
                if not config.quiet:
                    print_operation_summary(summary)
                return CanonicalizeResult(
                    success=True,
                    repairs={},
                    node_id_collisions=node_collisions,
                    edge_collisions=edge_collisions,
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

            if config.dry_run:
                message = "Dry run — would repair: " + ", ".join(
                    f"{variant} → {target}" for variant, target in sorted(repairs.items())
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

            db.conn.execute("BEGIN TRANSACTION")
            try:
                db.conn.execute("CREATE OR REPLACE TEMP TABLE _prefix_repairs (variant VARCHAR, canonical VARCHAR)")
                db.conn.executemany("INSERT INTO _prefix_repairs VALUES (?, ?)", list(repairs.items()))

                # DuckDB refuses to commit a transaction that ALTERs a table
                # after UPDATEing it, so add every original_* column first.
                if _table_columns(db, "nodes"):
                    ensure_slots(db.conn, "nodes", [nodes.original_id])
                if _table_columns(db, "edges"):
                    ensure_slots(db.conn, "edges", [edges.original_subject, edges.original_object])

                node_ids_rewritten = _rewrite_column(db, "nodes", nodes.id, nodes.original_id)
                edge_subjects_rewritten = _rewrite_column(db, "edges", edges.subject, edges.original_subject)
                edge_objects_rewritten = _rewrite_column(db, "edges", edges.object, edges.original_object)
                node_collisions, edge_collisions = _count_collisions(db)

                db.conn.execute("DROP TABLE _prefix_repairs")
                db.conn.execute("COMMIT")
            except Exception:
                # DuckDB may already have aborted the transaction; don't let a
                # failed ROLLBACK mask the original error.
                try:
                    db.conn.execute("ROLLBACK")
                except Exception as rollback_error:
                    logger.debug(f"ROLLBACK after canonicalize failure: {rollback_error}")
                raise

            _warn_collisions(warnings, node_collisions, edge_collisions)

            total = node_ids_rewritten + edge_subjects_rewritten + edge_objects_rewritten
            message = (
                f"Canonicalized {len(repairs)} prefixes "
                f"({', '.join(f'{v} → {t}' for v, t in sorted(repairs.items()))}); "
                f"rewrote {total:,} references"
            )
            summary = _summary(True, message, db, total, start_time, warnings, errors)
            if not config.quiet:
                print_operation_summary(summary)

            return CanonicalizeResult(
                success=True,
                repairs=repairs,
                node_ids_rewritten=node_ids_rewritten,
                edge_subjects_rewritten=edge_subjects_rewritten,
                edge_objects_rewritten=edge_objects_rewritten,
                node_id_collisions=node_collisions,
                edge_collisions=edge_collisions,
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
_NON_ID_TABLES = {"nodes", "edges", "file_schemas", _KOZA_SCHEMA_TABLE}


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


def _rewrite_column(db: GraphDatabase, table: str, column: str, original_column: str) -> int:
    """
    Rewrite one CURIE column via the _prefix_repairs temp table. Returns rows changed.

    ``original_column`` must already exist (see canonicalize_graph).
    """
    if not _table_columns(db, table):
        return 0

    result = db.conn.execute(f"""
        UPDATE {table}
        SET {original_column} = COALESCE({original_column}, {column}),
            {column} = r.canonical || substr({column}, length(r.variant) + 1)
        FROM _prefix_repairs r
        WHERE split_part({table}.{column}, ':', 1) = r.variant
    """).fetchone()
    return result[0] if result else 0


def _count_collisions(db: GraphDatabase) -> tuple[int, int]:
    """
    Count collisions involving rewritten ids.

    Returns (node ids shared by more than one node row where at least one row
    was rewritten, subject/predicate/object triples shared by more than one
    edge row where at least one row was rewritten). Tables or columns that do
    not exist contribute 0.
    """
    node_collisions = 0
    node_cols = _table_columns(db, "nodes")
    if {nodes.id, nodes.original_id} <= node_cols:
        node_collisions = db.conn.execute(f"""
            SELECT COUNT(*) FROM (
                SELECT {nodes.id}
                FROM nodes
                GROUP BY {nodes.id}
                HAVING COUNT(*) > 1
                   AND bool_or({nodes.original_id} IS NOT NULL AND {nodes.original_id} != {nodes.id})
            )
        """).fetchone()[0]

    edge_collisions = 0
    edge_cols = _table_columns(db, "edges")
    spo = {edges.subject, edges.predicate, edges.object}
    rewritten = [
        f"({orig} IS NOT NULL AND {orig} != {col})"
        for orig, col in ((edges.original_subject, edges.subject), (edges.original_object, edges.object))
        if orig in edge_cols
    ]
    if spo <= edge_cols and rewritten:
        edge_collisions = db.conn.execute(f"""
            SELECT COUNT(*) FROM (
                SELECT 1
                FROM edges
                GROUP BY {edges.subject}, {edges.predicate}, {edges.object}
                HAVING COUNT(*) > 1 AND bool_or({" OR ".join(rewritten)})
            )
        """).fetchone()[0]

    return node_collisions, edge_collisions


def _warn_collisions(warnings: list[str], node_collisions: int, edge_collisions: int) -> None:
    """Warn about rewritten ids that now duplicate existing nodes/edges."""
    if node_collisions:
        _warn(
            warnings,
            f"{node_collisions} node ids are shared by more than one row after canonicalization "
            f"(a repaired id landed on an existing one). The rows are kept as-is, not merged; "
            f"find them with: SELECT * FROM nodes WHERE id IN "
            f"(SELECT id FROM nodes GROUP BY id HAVING COUNT(*) > 1)",
        )
    if edge_collisions:
        _warn(
            warnings,
            f"{edge_collisions} subject/predicate/object triples are shared by more than one edge "
            f"after canonicalization. The rows are kept as-is, not merged; id-based edge "
            f"deduplication will not catch them if their ids differ.",
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
