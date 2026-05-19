"""Closurize engine — vendored from `closurizer` (monarch-initiative/closurizer)
in May 2026, with the view-based architecture applied. Closurizer the
standalone package is deprecated in favor of `koza.graph_operations.closurize`.

The wider operation surface (config, schema-seam integration, CLI command)
lives in `closurize.py`; this module is the SQL machinery.
"""

from typing import List, Optional

import os
import duckdb
from loguru import logger

def edge_columns(field: str, include_closure_fields: bool =True, node_column_names: list = None):
    column_text = f"""
       {field}.name as {field}_label, 
       {field}.category as {field}_category,
       {field}.namespace as {field}_namespace,       
    """
    if include_closure_fields:
        column_text += f"""
        {field}_closure.closure as {field}_closure,
        {field}_closure_label.closure_label as {field}_closure_label,
        """

    # Only add taxon fields if they exist in the nodes table
    if field in ['subject', 'object'] and node_column_names:
        if 'in_taxon' in node_column_names:
            column_text += f"""
        {field}.in_taxon as {field}_taxon,"""
        if 'in_taxon_label' in node_column_names:
            column_text += f"""
        {field}.in_taxon_label as {field}_taxon_label,"""
        column_text += """
        """
    return column_text

def edge_joins(field: str, include_closure_joins: bool =True, is_multivalued: bool = False):
    if is_multivalued:
        # For VARCHAR[] fields, use array containment with list_contains
        join_condition = f"list_contains(edges.{field}, {field}.id)"
    else:
        # For VARCHAR fields, use direct equality
        join_condition = f"edges.{field} = {field}.id"
    
    joins = f"""
    left outer join nodes as {field} on {join_condition}"""
    
    if include_closure_joins:
        joins += f"""
    left outer join closure_id as {field}_closure on {field}.id = {field}_closure.id
    left outer join closure_label as {field}_closure_label on {field}.id = {field}_closure_label.id"""
    
    return joins + "\n    "

def evidence_count_expr(evidence_fields: List[str], edges_column_names: list = None) -> str:
    """SQL expression that sums lengths of each evidence field (VARCHAR[] arrays).

    Returns just the expression, no alias; the caller decides whether to
    project it inline in a SELECT or materialize it as a column.
    """
    parts = [
        f"ifnull(array_length({field}),0)"
        for field in evidence_fields
        if not edges_column_names or field in edges_column_names
    ]
    return "+".join(parts) if parts else "0"


def grouping_key_expr(grouping_fields, edges_column_names: list = None) -> str:
    """SQL expression for the grouping key. Returns just the expression."""
    if not grouping_fields:
        return "null"
    fragments = []
    for field in grouping_fields:
        if not edges_column_names or field in edges_column_names:
            if field == 'negated':
                fragments.append(f"coalesce(cast({field} as varchar).replace('true','NOT'), '')")
            else:
                fragments.append(field)
    if not fragments:
        return "null"
    return f"concat_ws('|', {', '.join(fragments)})"


def _drop_any(name: str, db) -> None:
    """Drop `name` whether it's a view or a table. DuckDB's `DROP X IF EXISTS`
    errors on type mismatch, so we have to look up the type first."""
    row = db.sql(
        f"SELECT table_type FROM information_schema.tables WHERE table_name = '{name}'"
    ).fetchone()
    if row is None:
        return
    kind = "VIEW" if row[0] == "VIEW" else "TABLE"
    db.sql(f"DROP {kind} {name}")


def build_node_predicate_side_table(
    db,
    predicate: str,
    additional_filter: Optional[str] = None,
) -> str:
    """Build a per-predicate node-extension side table aggregating object info
    for edges where nodes.id is the subject and the edge has the given predicate.

    Joins base tables (edges + nodes for object label + closure_id/_label)
    directly, never through denormalized_edges, so memory pressure is bounded
    by one predicate's edge subset.

    Returns the side table name; columns are (id, <field>, <field>_label,
    <field>_count, <field>_closure, <field>_closure_label).
    """
    field = predicate.replace("biolink:", "")
    side_table = f"node_{field}"
    extra = f"AND ({additional_filter})" if additional_filter else ""
    db.sql(f"""
    CREATE OR REPLACE TABLE {side_table} AS
    SELECT
      n.id,
      CASE WHEN COUNT(DISTINCT e.object) > 0
           THEN ARRAY_AGG(DISTINCT e.object)
           ELSE NULL END AS {field},
      CASE WHEN COUNT(DISTINCT o.name) > 0
           THEN ARRAY_AGG(DISTINCT o.name)
           ELSE NULL END AS {field}_label,
      COUNT(DISTINCT e.object) AS {field}_count,
      CASE WHEN COUNT(c.closure) > 0
           THEN LIST_DISTINCT(FLATTEN(ARRAY_AGG(c.closure)))
           ELSE NULL END AS {field}_closure,
      CASE WHEN COUNT(cl.closure_label) > 0
           THEN LIST_DISTINCT(FLATTEN(ARRAY_AGG(cl.closure_label)))
           ELSE NULL END AS {field}_closure_label
    FROM nodes n
    LEFT JOIN edges e
      ON n.id = e.subject
     AND e.predicate = 'biolink:{field}'
     {extra}
    LEFT JOIN nodes o ON e.object = o.id
    LEFT JOIN closure_id c ON e.object = c.id
    LEFT JOIN closure_label cl ON e.object = cl.id
    GROUP BY n.id
    """)
    return side_table


def materialize_column(db, table: str, column_name: str, expression: str, sql_type: str):
    """Idempotently add a computed column to a table: drop if present, add, populate."""
    cols = {r[0] for r in db.sql(f"DESCRIBE {table}").fetchall()}
    if column_name in cols:
        db.sql(f"alter table {table} drop column {column_name}")
    db.sql(f"alter table {table} add column {column_name} {sql_type}")
    db.sql(f"update {table} set {column_name} = {expression}")




def add_closure(closure_file: str,
                database_path: str,
                node_fields: Optional[List[str]] = None,
                edge_fields: Optional[List[str]] = None,
                edge_fields_to_label: Optional[List[str]] = None,
                additional_node_constraints: Optional[str] = None,
                evidence_fields: Optional[List[str]] = None,
                grouping_fields: Optional[List[str]] = None,
                ):
    """Apply closure expansion to the nodes/edges tables in `database_path`.

    The DuckDB at `database_path` must already contain `nodes` and `edges`
    tables (produced upstream by `koza join`). `closure_file` is a TSV with
    `(subject_id, predicate_id, object_id)` columns (e.g. the filtered
    phenio relation graph).

    Produces:
    - Materialized closure side tables: `closure_id`, `closure_label`,
      `descendants_id`, `descendants_label`.
    - New columns on `edges`: `evidence_count`, `grouping_key`.
    - One materialized side table per `node_fields` entry: `node_<predicate>`.
    - `denormalized_edges` VIEW and `denormalized_nodes` VIEW.

    `additional_node_constraints`: optional SQL fragment applied to the
    per-predicate side-table edges join. Use `e.<col>` to reference edges
    columns (e.g. `"e.negated IS NULL OR e.negated = false"`).

    Set `DUCKDB_MEMORY_LIMIT` env var to cap DuckDB memory and force spill.
    """
    node_fields = list(node_fields or [])
    edge_fields = list(edge_fields or ['subject', 'object'])
    edge_fields_to_label = list(edge_fields_to_label or [])
    evidence_fields = list(evidence_fields or ['has_evidence', 'publications'])
    grouping_fields = list(grouping_fields or ['subject', 'negated', 'predicate', 'object'])

    if not os.path.exists(database_path):
        raise ValueError(f"database_path does not exist: {database_path}")

    logger.info(f"Closurize: database={database_path}, closure_file={closure_file}")

    db = duckdb.connect(database=database_path)
    if mem := os.environ.get("DUCKDB_MEMORY_LIMIT"):
        db.sql(f"PRAGMA memory_limit='{mem}'")

    # Add namespace column if not present — derived from id prefix.
    node_column_names = [col[0] for col in db.sql("DESCRIBE nodes").fetchall()]
    if 'namespace' not in node_column_names:
        logger.debug("Adding namespace column to nodes")
        db.sql("ALTER TABLE nodes ADD COLUMN namespace VARCHAR")
        db.sql("UPDATE nodes SET namespace = substr(id, 1, instr(id,':') - 1)")

    # Build closure side tables from the relation-graph TSV.
    db.sql(f"""
        CREATE OR REPLACE TABLE closure AS
        SELECT * FROM read_csv(
            '{closure_file}',
            sep='\t',
            names=['subject_id', 'predicate_id', 'object_id'],
            AUTO_DETECT=TRUE
        )
    """)
    db.sql("""
        CREATE OR REPLACE TABLE closure_id AS
        SELECT subject_id AS id, ARRAY_AGG(object_id) AS closure
        FROM closure GROUP BY subject_id
    """)
    db.sql("""
        CREATE OR REPLACE TABLE closure_label AS
        SELECT subject_id AS id, ARRAY_AGG(name) AS closure_label
        FROM closure JOIN nodes ON object_id = id
        GROUP BY subject_id
    """)
    db.sql("""
        CREATE OR REPLACE TABLE descendants_id AS
        SELECT object_id AS id, ARRAY_AGG(subject_id) AS descendants
        FROM closure GROUP BY object_id
    """)
    db.sql("""
        CREATE OR REPLACE TABLE descendants_label AS
        SELECT object_id AS id, ARRAY_AGG(name) AS descendants_label
        FROM closure JOIN nodes ON subject_id = nodes.id
        GROUP BY object_id
    """)

    # Materialize per-edge derived columns onto `edges` itself: evidence_count
    # and grouping_key are computed from edges columns only, cheap to store,
    # and survive across re-runs / external queries on the base table.
    edges_table_info = db.sql("DESCRIBE edges").fetchall()
    edges_table_types = {col[0]: col[1] for col in edges_table_info}
    edges_column_names = [col[0] for col in edges_table_info]
    materialize_column(
        db, "edges", "evidence_count",
        evidence_count_expr(evidence_fields, edges_column_names),
        "BIGINT",
    )
    materialize_column(
        db, "edges", "grouping_key",
        grouping_key_expr(grouping_fields, edges_column_names),
        "VARCHAR",
    )
    # Refresh column lists since edges just gained two columns.
    edges_table_info = db.sql("DESCRIBE edges").fetchall()
    edges_table_types = {col[0]: col[1] for col in edges_table_info}
    edges_column_names = [col[0] for col in edges_table_info]
    node_column_names = [r[0] for r in db.sql("DESCRIBE nodes").fetchall()]

    # Build edge joins with VARCHAR[] handling based on actual column types.
    def _is_mv(field: str) -> bool:
        return "VARCHAR[]" in edges_table_types.get(field, "").upper()

    edge_field_joins = [edge_joins(field, is_multivalued=_is_mv(field)) for field in edge_fields]
    edge_field_to_label_joins = [
        edge_joins(field, include_closure_joins=False, is_multivalued=_is_mv(field))
        for field in edge_fields_to_label
    ]

    # Exclude any edges columns that would collide with the join expansions.
    collision_cols = {
        f"{field}_{suffix}"
        for field in edge_fields + edge_fields_to_label
        for suffix in ("label", "category", "namespace", "closure", "closure_label", "taxon", "taxon_label")
    }
    excluded = [c for c in collision_cols if c in edges_column_names]
    edges_select = f"edges.* EXCLUDE ({', '.join(excluded)})" if excluded else "edges.*"

    column_projections = [
        edge_columns(field, node_column_names=node_column_names)
        for field in edge_fields
    ] + [
        edge_columns(field, include_closure_fields=False, node_column_names=node_column_names)
        for field in edge_fields_to_label
    ]

    _drop_any("denormalized_edges", db)
    db.sql(f"""
        CREATE OR REPLACE VIEW denormalized_edges AS
        SELECT
            {edges_select},
            {''.join(column_projections)}
        FROM edges
            {''.join(edge_field_joins)}
            {''.join(edge_field_to_label_joins)}
    """)

    # Build one side table per configured node predicate, each bounded by
    # that predicate's edge subset — no monolithic GROUP BY.
    side_table_joins = []
    side_table_columns = []
    for node_field in node_fields:
        field = node_field.replace("biolink:", "")
        side_table = build_node_predicate_side_table(db, node_field, additional_node_constraints)
        alias = f"_{field}"
        side_table_joins.append(f"LEFT JOIN {side_table} {alias} ON nodes.id = {alias}.id")
        for col in (field, f"{field}_label", f"{field}_count",
                    f"{field}_closure", f"{field}_closure_label"):
            side_table_columns.append(f"{alias}.{col}")

    column_list = (", ".join(side_table_columns) + ",") if side_table_columns else ""
    _drop_any("denormalized_nodes", db)
    db.sql(f"""
        CREATE OR REPLACE VIEW denormalized_nodes AS
        SELECT
            nodes.*,
            {column_list}
            _d.descendants AS has_descendant,
            _dl.descendants_label AS has_descendant_label,
            COALESCE(ARRAY_LENGTH(_d.descendants), 0) AS has_descendant_count
        FROM nodes
        {chr(10).join(side_table_joins)}
        LEFT JOIN descendants_id _d ON nodes.id = _d.id
        LEFT JOIN descendants_label _dl ON nodes.id = _dl.id
    """)
