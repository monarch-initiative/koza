"""Biolink edge-type and node-prefix validation.

Two checks, both Biolink-driven and both run as set-operations over the graph's
own ``nodes`` / ``edges`` — no row-by-row Python:

* **subobj_errors** — where does each edge type *mismatch* the current Biolink
  model's domain/range? A mismatch is NOT a verdict on the data: Biolink's
  domain/range is stricter than widely realized, so a mismatch may be resolved by
  loosening the model just as often as by fixing the data — the report is the
  triage input, and the edge count + how broadly a mismatch occurs is the signal
  (a million edges across sources points at the model; a handful points at the
  data). *Tiered*: an edge that **asserts** its association class (the edge
  ``category`` slot) is checked against THAT class's descendant-expanded
  subject/predicate/object constraints (BAD_SUBJECT / BAD_PREDICATE / BAD_OBJECT /
  BAD_COMBINATION); edges
  asserting no constrained class fall back to "is this triple in the legal union
  at all" (NOT_IN_LEGAL_TYPES — *advisory*, the union has coverage holes). Emitted
  at edge-type (summary) grain, so each mismatch carries its edge count.
* **prefix_errors** — is each node's CURIE prefix valid for its category?

Both handle ``category`` as **scalar** (monarch-kg forces single-valued) or
**list** (translator keeps it multivalued): every category column is coerced to
a list before unnesting, and a graph whose edges carry no ``category`` slot at
all simply gets the fallback union check throughout.

The Biolink lookups (:func:`build_edge_type_constraints`,
:func:`build_category_prefixes`) are registered as DuckDB relations, so the graph
database stays opened read-only.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
from loguru import logger

from koza.graph_operations.biolink_constraints import (
    build_category_prefixes,
    build_edge_type_constraints,
)
from koza.graph_operations.graph_schema import load_biolink_schemaview
from koza.model.graph_operations import (
    TabularReportFormat,
    BiolinkCheckConfig,
    BiolinkCheckResult,
)

from .utils import GraphDatabase

# Mismatch verdicts. Named neutrally (a mismatch may be a model gap, not a data
# error). Rows where we can't resolve a category (dangling/missing endpoint) are
# out of scope here — dangling edges are a separate QC report.
_VIOLATION_VERDICTS = (
    "BAD_SUBJECT",
    "BAD_PREDICATE",
    "BAD_OBJECT",
    "BAD_COMBINATION",
    "NOT_IN_LEGAL_TYPES",
)


def _describe(conn, table: str) -> dict[str, str]:
    return {r[0]: r[1] for r in conn.execute(f"DESCRIBE {table}").fetchall()}


def _to_list_expr(qualified_col: str, dtype: str) -> str:
    """SQL expression coercing a (possibly NULL, possibly scalar) category column
    to a ``VARCHAR[]`` — empty list when NULL so it contributes nothing."""
    if dtype.upper().rstrip().endswith("[]"):
        return f"coalesce({qualified_col}, CAST([] AS VARCHAR[]))"
    return (
        f"CASE WHEN {qualified_col} IS NULL THEN CAST([] AS VARCHAR[]) "
        f"ELSE [CAST({qualified_col} AS VARCHAR)] END"
    )


def _biolink_prefixed(expr: str) -> str:
    """Add a ``biolink:`` prefix to a scalar that has no CURIE prefix.

    Some graphs strip it (monarch-kg stores ``Gene``, not ``biolink:Gene``), and a
    graph can even be inconsistent (bare category, prefixed predicate). The
    Biolink lookups are all ``biolink:`` CURIEs, so normalize before comparing."""
    return f"CASE WHEN {expr} LIKE '%:%' THEN {expr} ELSE 'biolink:' || {expr} END"


def _category_list_expr(qualified_col: str, dtype: str) -> str:
    """List-coerced category column with every element normalized to ``biolink:``."""
    list_expr = _to_list_expr(qualified_col, dtype)
    return f"list_transform({list_expr}, x -> {_biolink_prefixed('x')})"


def _register_constraint_relations(conn, constraints, prefix_rows) -> None:
    """Register the Biolink lookups as DuckDB relations (keeps the graph read-only)."""
    conn.register("_assoc_subj", pd.DataFrame(constraints.subject_rows(), columns=["association_class", "subject_category"]))
    conn.register("_assoc_pred", pd.DataFrame(constraints.predicate_rows(), columns=["association_class", "predicate"]))
    conn.register("_assoc_obj", pd.DataFrame(constraints.object_rows(), columns=["association_class", "object_category"]))
    conn.register("_union", pd.DataFrame(constraints.union_rows(), columns=["subject_category", "predicate", "object_category"]))
    conn.register("_category_prefixes", pd.DataFrame(prefix_rows, columns=["category", "prefix"]))


def _edge_type_summary_view(conn) -> None:
    """Build ``_val_summary``: edge-type grain with list-coerced category columns.

    Asserted edge category comes from the edges table's own ``category`` slot when
    present (else an empty list → every edge uses the fallback union check)."""
    edge_cols = _describe(conn, "edges")
    node_cols = _describe(conn, "nodes")
    node_cat = node_cols.get("category", "VARCHAR")

    subj = _category_list_expr("sn.category", node_cat)
    obj = _category_list_expr("on_.category", node_cat)
    if "category" in edge_cols:
        assoc = _category_list_expr("e.category", edge_cols["category"])
    else:
        assoc = "CAST([] AS VARCHAR[])"

    conn.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW _val_summary AS
        SELECT assoc_category, subject_category, predicate, object_category, count(*) AS count
        FROM (
            SELECT {assoc} AS assoc_category,
                   {subj}  AS subject_category,
                   {_biolink_prefixed('e.predicate')} AS predicate,
                   {obj}   AS object_category
            FROM edges e
            LEFT JOIN nodes sn ON e.subject = sn.id
            LEFT JOIN nodes on_ ON e.object = on_.id
        )
        -- both endpoints must resolve to a category to be validatable (else dangling)
        WHERE len(subject_category) > 0 AND len(object_category) > 0
        GROUP BY ALL
        """
    )


_JUDGE_SQL = """
WITH judged AS (
    SELECT s.*,
        EXISTS(SELECT 1 FROM UNNEST(s.assoc_category) t(c)
               WHERE c IN (SELECT association_class FROM _assoc_subj)) AS is_constrained,
        EXISTS(
            SELECT 1 FROM UNNEST(s.assoc_category) t(c)
            WHERE c IN (SELECT association_class FROM _assoc_subj)
              AND EXISTS(SELECT 1 FROM _assoc_subj a, UNNEST(s.subject_category) ss(sc)
                         WHERE a.association_class = c AND a.subject_category = ss.sc)
              AND EXISTS(SELECT 1 FROM _assoc_pred a
                         WHERE a.association_class = c AND a.predicate = s.predicate)
              AND EXISTS(SELECT 1 FROM _assoc_obj a, UNNEST(s.object_category) oo(oc)
                         WHERE a.association_class = c AND a.object_category = oo.oc)
        ) AS strict_ok,
        EXISTS(SELECT 1 FROM _assoc_subj a, UNNEST(s.assoc_category) t(c), UNNEST(s.subject_category) ss(sc)
               WHERE a.association_class = c AND a.subject_category = ss.sc) AS subj_ok,
        EXISTS(SELECT 1 FROM _assoc_pred a, UNNEST(s.assoc_category) t(c)
               WHERE a.association_class = c AND a.predicate = s.predicate) AS pred_ok,
        EXISTS(SELECT 1 FROM _assoc_obj a, UNNEST(s.assoc_category) t(c), UNNEST(s.object_category) oo(oc)
               WHERE a.association_class = c AND a.object_category = oo.oc) AS obj_ok,
        EXISTS(SELECT 1 FROM _union u, UNNEST(s.subject_category) ss(sc), UNNEST(s.object_category) oo(oc)
               WHERE u.subject_category = ss.sc AND u.predicate = s.predicate AND u.object_category = oo.oc) AS union_ok
    FROM _val_summary s
)
SELECT subject_category, predicate, object_category,
       list_distinct(assoc_category) AS asserted_categories,
       is_constrained AS strict_checked,
       count,
       CASE
           WHEN is_constrained AND strict_ok    THEN 'ok'
           WHEN is_constrained AND NOT subj_ok  THEN 'BAD_SUBJECT'
           WHEN is_constrained AND NOT pred_ok  THEN 'BAD_PREDICATE'
           WHEN is_constrained AND NOT obj_ok   THEN 'BAD_OBJECT'
           WHEN is_constrained                  THEN 'BAD_COMBINATION'
           WHEN union_ok                        THEN 'ok'
           ELSE 'NOT_IN_LEGAL_TYPES'
       END AS verdict
    FROM judged
"""

# A node is valid if its prefix is admitted by ANY of its categories — a
# multivalued node that is a Gene (admits NCBIGene) is fine even though its list
# also carries Protein/Polypeptide (which don't). It only violates when at least
# one of its categories declares prefixes and NONE of them admit this prefix.
_PREFIX_SQL_TEMPLATE = """
WITH np AS (
    SELECT id, split_part(id, ':', 1) AS prefix, {node_cat} AS categories
    FROM nodes WHERE id IS NOT NULL
),
judged AS (
    SELECT id, prefix, categories,
        EXISTS(SELECT 1 FROM _category_prefixes cp, UNNEST(categories) t(cat)
               WHERE cp.category = t.cat) AS any_category_constrains,
        EXISTS(SELECT 1 FROM _category_prefixes cp, UNNEST(categories) t(cat)
               WHERE cp.category = t.cat AND cp.prefix = np.prefix) AS prefix_ok
    FROM np
)
SELECT prefix, list_sort(categories) AS categories,
       count(DISTINCT id) AS n_nodes,
       array_agg(DISTINCT id)[1:5] AS examples
FROM judged
WHERE any_category_constrains AND NOT prefix_ok
GROUP BY 1, 2
ORDER BY n_nodes DESC
"""


def _copy_out(conn, query: str, path: Path, fmt: TabularReportFormat) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == TabularReportFormat.PARQUET:
        conn.execute(f"COPY ({query}) TO '{path}' (FORMAT PARQUET)")
    elif fmt == TabularReportFormat.JSONL:
        conn.execute(f"COPY ({query}) TO '{path}' (FORMAT JSON)")
    else:
        conn.execute(f"COPY ({query}) TO '{path}' (HEADER, DELIMITER '\\t')")
    return conn.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()[0]


def run_biolink_check(config: BiolinkCheckConfig) -> BiolinkCheckResult:
    """Validate a graph's edge types and node prefixes against Biolink.

    Writes ``subobj_errors`` and ``prefix_errors`` (one violation row each, at
    edge-type / (category, prefix) grain) to ``config.output_dir`` when set.
    """
    start = time.time()
    sv = load_biolink_schemaview()
    constraints = build_edge_type_constraints(sv)
    prefix_rows = build_category_prefixes(sv)

    ext = {TabularReportFormat.PARQUET: "parquet", TabularReportFormat.JSONL: "jsonl"}.get(
        config.output_format, "tsv"
    )

    with GraphDatabase(config.database_path, read_only=True) as db:
        conn = db.conn
        _register_constraint_relations(conn, constraints, prefix_rows)

        # --- edge-type validation ---
        _edge_type_summary_view(conn)
        verdict_list = ", ".join(f"'{v}'" for v in _VIOLATION_VERDICTS)
        subobj_query = f"SELECT * FROM ({_JUDGE_SQL}) WHERE verdict IN ({verdict_list}) ORDER BY count DESC"
        subobj_errors = subobj_strict = subobj_advisory = 0
        if config.output_dir:
            out = config.output_dir / f"subobj_errors.{ext}"
            subobj_errors = _copy_out(conn, subobj_query, out, config.output_format)
        counts = conn.execute(
            f"SELECT strict_checked, count(*) FROM ({_JUDGE_SQL}) "
            f"WHERE verdict IN ({verdict_list}) GROUP BY 1"
        ).fetchall()
        for strict, n in counts:
            if strict:
                subobj_strict += n
            else:
                subobj_advisory += n

        # --- node-prefix validation ---
        node_cat = _describe(conn, "nodes").get("category", "VARCHAR")
        prefix_query = _PREFIX_SQL_TEMPLATE.format(node_cat=_category_list_expr("category", node_cat))
        prefix_errors = 0
        if config.output_dir:
            out = config.output_dir / f"prefix_errors.{ext}"
            prefix_errors = _copy_out(conn, prefix_query, out, config.output_format)
        else:
            prefix_errors = conn.execute(f"SELECT COUNT(*) FROM ({prefix_query})").fetchone()[0]

    result = BiolinkCheckResult(
        database_path=config.database_path,
        output_dir=config.output_dir,
        subobj_error_types=subobj_errors if config.output_dir else (subobj_strict + subobj_advisory),
        subobj_strict_error_types=subobj_strict,
        subobj_advisory_error_types=subobj_advisory,
        prefix_error_types=prefix_errors,
        total_time_seconds=time.time() - start,
    )
    if not config.quiet:
        logger.info(
            f"Validation: {result.subobj_strict_error_types} strict + "
            f"{result.subobj_advisory_error_types} advisory edge-type violations, "
            f"{result.prefix_error_types} prefix violations"
        )
    return result
