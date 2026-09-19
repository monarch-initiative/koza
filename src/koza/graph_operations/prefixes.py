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

from .graph_schema import ensure_slots
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

    with GraphDatabase(config.database_path) as db:
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
    prefix that matches a canonical prefix case-insensitively but not exactly.
    Original identifiers are preserved in ``original_id`` /
    ``original_subject`` / ``original_object`` (existing values in those
    columns are never overwritten). Unknown prefixes are left untouched.

    A rewrite can land a repaired node id on an id the graph already has
    (``hgnc:746`` arriving at an existing ``HGNC:746`` row). Those collisions
    are counted and reported as warnings; resolving them is deduplication and
    is left to the dedup machinery.

    Args:
        config: CanonicalizeConfig with database_path, context, dry_run, quiet.

    Returns:
        CanonicalizeResult with the applied repairs and rewrite counts.
    """
    start_time = time.time()
    errors: list[str] = []
    warnings: list[str] = []

    try:
        canonical = load_canonical_prefixes(config.context)

        with GraphDatabase(config.database_path) as db:
            usages = _classify(_prefix_census(db), canonical)
            repairs = {
                u.prefix: u.canonical_prefix for u in usages if u.status == PrefixStatus.CASE_VARIANT
            }

            if not repairs:
                message = f"No case-variant prefixes found against context {config.context!r}"
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

            db.conn.execute("CREATE TEMP TABLE _prefix_repairs (variant VARCHAR, canonical VARCHAR)")
            db.conn.executemany(
                "INSERT INTO _prefix_repairs VALUES (?, ?)", list(repairs.items())
            )

            node_ids_rewritten = _rewrite_column(db, "nodes", nodes.id, nodes.original_id)
            edge_subjects_rewritten = _rewrite_column(db, "edges", edges.subject, edges.original_subject)
            edge_objects_rewritten = _rewrite_column(db, "edges", edges.object, edges.original_object)
            collisions = _count_node_collisions(db)

            if collisions:
                warning = (
                    f"{collisions} repaired node ids collide with ids already in the graph; "
                    f"run deduplication to fold them."
                )
                warnings.append(warning)
                logger.warning(warning)

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
                node_id_collisions=collisions,
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


def _rewrite_column(db: GraphDatabase, table: str, column: str, original_column: str) -> int:
    """Rewrite one CURIE column via the _prefix_repairs temp table. Returns rows changed."""
    tables = {
        row[0]
        for row in db.conn.execute(
            f"SELECT table_name FROM information_schema.tables WHERE table_name = '{table}'"
        ).fetchall()
    }
    if not tables:
        return 0

    ensure_slots(db.conn, table, [original_column])
    result = db.conn.execute(f"""
        UPDATE {table}
        SET {original_column} = COALESCE({original_column}, {column}),
            {column} = r.canonical || substr({column}, length(r.variant) + 1)
        FROM _prefix_repairs r
        WHERE split_part({table}.{column}, ':', 1) = r.variant
    """).fetchone()
    return result[0] if result else 0


def _count_node_collisions(db: GraphDatabase) -> int:
    """Count distinct repaired node ids that now collide with another node row."""
    result = db.conn.execute(f"""
        SELECT COUNT(DISTINCT n.{nodes.id})
        FROM nodes n
        WHERE n.original_id IS NOT NULL
          AND n.original_id != n.{nodes.id}
          AND EXISTS (
            SELECT 1 FROM nodes m
            WHERE m.{nodes.id} = n.{nodes.id} AND m.rowid != n.rowid
          )
    """).fetchone()
    return result[0] if result else 0


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
