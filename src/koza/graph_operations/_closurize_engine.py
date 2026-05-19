"""Closurize engine — vendored from `closurizer` (monarch-initiative/closurizer)
in May 2026, with the view-based architecture applied. Closurizer the
standalone package is deprecated in favor of `koza.graph_operations.closurize`.

The wider operation surface (config, schema-seam integration, CLI command)
lives in `closurize.py`; this module is the SQL machinery.
"""

from typing import List, Optional

import os
import tarfile
import duckdb

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


def evidence_sum(evidence_fields: List[str], edges_column_names: list = None):
    """Backwards-compatible wrapper returning the full SELECT-projection form."""
    return f"{evidence_count_expr(evidence_fields, edges_column_names)} as evidence_count,"


def node_columns(predicate):
    # strip the biolink predicate, if necessary to get the field name
    field = predicate.replace('biolink:','')

    return f"""
    case when count(distinct {field}_edges.object) > 0 then array_agg(distinct {field}_edges.object) else null end as {field},
    case when count(distinct {field}_edges.object_label) > 0 then array_agg(distinct {field}_edges.object_label) else null end as {field}_label,
    count (distinct {field}_edges.object) as {field}_count,
    case when count({field}_closure.closure) > 0 then list_distinct(flatten(array_agg({field}_closure.closure))) else null end as {field}_closure,
    case when count({field}_closure_label.closure_label) > 0 then list_distinct(flatten(array_agg({field}_closure_label.closure_label))) else null end as {field}_closure_label,
    """

def node_joins(predicate):
    # strip the biolink predicate, if necessary to get the field name
    field = predicate.replace('biolink:','')
    return f"""
      left outer join denormalized_edges as {field}_edges 
        on nodes.id = {field}_edges.subject 
           and {field}_edges.predicate = 'biolink:{field}'
      left outer join closure_id as {field}_closure
        on {field}_edges.object = {field}_closure.id
      left outer join closure_label as {field}_closure_label
        on {field}_edges.object = {field}_closure_label.id
    """


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


def grouping_key(grouping_fields, edges_column_names: list = None):
    """Backwards-compatible wrapper returning the full SELECT-projection form."""
    return f"{grouping_key_expr(grouping_fields, edges_column_names)} as grouping_key"


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




def load_from_archive(kg_archive: str, db, multivalued_fields: List[str]):
    """Load nodes and edges tables from tar.gz archive"""
    
    tar = tarfile.open(f"{kg_archive}")

    print("Loading node table...")
    node_file_name = [member.name for member in tar.getmembers() if member.name.endswith('_nodes.tsv') ][0]
    tar.extract(node_file_name,)
    node_file = f"{node_file_name}"
    print(f"node_file: {node_file}")

    db.sql(f"""
    create or replace table nodes as select *,  substr(id, 1, instr(id,':') -1) as namespace from read_csv('{node_file_name}', header=True, sep='\t', AUTO_DETECT=TRUE)
    """)

    edge_file_name = [member.name for member in tar.getmembers() if member.name.endswith('_edges.tsv') ][0]
    tar.extract(edge_file_name)
    edge_file = f"{edge_file_name}"
    print(f"edge_file: {edge_file}")

    db.sql(f"""
    create or replace table edges as select * from read_csv('{edge_file_name}', header=True, sep='\t', AUTO_DETECT=TRUE)
    """)
    
    # Convert multivalued fields to arrays
    prepare_multivalued_fields(db, multivalued_fields)
    
    # Clean up extracted files
    if os.path.exists(f"{node_file}"):
        os.remove(f"{node_file}")
    if os.path.exists(f"{edge_file}"):
        os.remove(f"{edge_file}")


def prepare_multivalued_fields(db, multivalued_fields: List[str]):
    """Convert specified fields to varchar[] arrays in both nodes and edges tables"""
    
    # Convert multivalued fields in nodes table to varchar[] arrays
    nodes_table_info = db.sql("DESCRIBE nodes").fetchall()
    node_column_names = [col[0] for col in nodes_table_info]
    node_column_types = {col[0]: col[1] for col in nodes_table_info}
    
    for field in multivalued_fields:
        if field in node_column_names:
            # Check if field is already VARCHAR[] - if so, skip conversion
            if 'VARCHAR[]' in node_column_types[field].upper():
                print(f"Field '{field}' in nodes table is already VARCHAR[], skipping conversion")
                continue
                
            print(f"Converting field '{field}' in nodes table to VARCHAR[]")
            # Create a new column with proper array type and replace the original
            db.sql(f"""
            alter table nodes add column {field}_array VARCHAR[]
            """)
            db.sql(f"""
            update nodes set {field}_array = 
                case 
                    when {field} is null or {field} = '' then null
                    else split({field}, '|')
                end
            """)
            db.sql(f"""
            alter table nodes drop column {field}
            """)
            db.sql(f"""
            alter table nodes rename column {field}_array to {field}
            """)

    # Convert multivalued fields in edges table to varchar[] arrays
    edges_table_info = db.sql("DESCRIBE edges").fetchall()
    edge_column_names = [col[0] for col in edges_table_info]
    edge_column_types = {col[0]: col[1] for col in edges_table_info}
    
    for field in multivalued_fields:
        if field in edge_column_names:
            # Check if field is already VARCHAR[] - if so, skip conversion
            if 'VARCHAR[]' in edge_column_types[field].upper():
                print(f"Field '{field}' in edges table is already VARCHAR[], skipping conversion")
                continue
                
            print(f"Converting field '{field}' in edges table to VARCHAR[]")
            # Create a new column with proper array type and replace the original
            db.sql(f"""
            alter table edges add column {field}_array VARCHAR[]
            """)
            db.sql(f"""
            update edges set {field}_array = 
                case 
                    when {field} is null or {field} = '' then null
                    else split({field}, '|')
                end
            """)
            db.sql(f"""
            alter table edges drop column {field}
            """)
            db.sql(f"""
            alter table edges rename column {field}_array to {field}
            """)


def add_closure(closure_file: str,
                nodes_output_file: str,
                edges_output_file: str,
                kg_archive: Optional[str] = None,
                database_path: str = 'monarch-kg.duckdb',
                node_fields: List[str] = [],
                edge_fields: List[str] = ['subject', 'object'],
                edge_fields_to_label: List[str] = [],
                additional_node_constraints: Optional[str] = None,
                dry_run: bool  = False,
                evidence_fields: List[str] = ['has_evidence', 'publications'],
                grouping_fields: List[str] = ['subject', 'negated', 'predicate', 'object'],
                multivalued_fields: List[str] = ['has_evidence', 'publications', 'in_taxon', 'in_taxon_label'],
                export_edges: bool = False,
                export_nodes: bool = False
                ):
    # Validate input parameters
    if not kg_archive and not os.path.exists(database_path):
        raise ValueError("Either kg_archive must be specified or database_path must exist")
    
    print("Generating closure KG...")
    if kg_archive:
        print(f"kg_archive: {kg_archive}")
    print(f"database_path: {database_path}")
    print(f"closure_file: {closure_file}")

    # Connect to database
    db = duckdb.connect(database=database_path)
    if os.environ.get("DUCKDB_MEMORY_LIMIT"):
        db.sql(f"PRAGMA memory_limit='{os.environ['DUCKDB_MEMORY_LIMIT']}'")

    if not dry_run:
        print(f"fields: {','.join(edge_fields)}")
        print(f"output_file: {edges_output_file}")

        # Load data based on input method
        if kg_archive:
            load_from_archive(kg_archive, db, multivalued_fields)
        else:
            # Database already exists and contains data
            # Check if namespace column exists, add it if needed
            node_column_names = [col[0] for col in db.sql("DESCRIBE nodes").fetchall()]
            if 'namespace' not in node_column_names:
                print("Adding namespace column to nodes table...")
                db.sql("ALTER TABLE nodes ADD COLUMN namespace VARCHAR")
                db.sql("UPDATE nodes SET namespace = substr(id, 1, instr(id,':') -1)")
            
            # Convert multivalued fields to arrays
            prepare_multivalued_fields(db, multivalued_fields)

        # Load the relation graph tsv in long format mapping a node to each of it's ancestors
        db.sql(f"""
        create or replace table closure as select * from read_csv('{closure_file}', sep='\t', names=['subject_id', 'predicate_id', 'object_id'], AUTO_DETECT=TRUE)
        """)

        db.sql("""
        create or replace table closure_id as select subject_id as id, array_agg(object_id) as closure from closure group by subject_id
        """)

        db.sql("""
        create or replace table closure_label as select subject_id as id, array_agg(name) as closure_label from closure join nodes on object_id = id
        group by subject_id
        """)

        db.sql("""
        create or replace table descendants_id as 
        select object_id as id, array_agg(subject_id) as descendants 
        from closure 
        group by object_id
        """)

        db.sql("""
        create or replace table descendants_label as 
        select object_id as id, array_agg(name) as descendants_label 
        from closure 
        join nodes on subject_id = nodes.id
        group by object_id
        """)

    # Get edges table schema to determine which fields are VARCHAR[]
    edges_table_info = db.sql("DESCRIBE edges").fetchall()
    edges_table_types = {col[0]: col[1] for col in edges_table_info}
    edges_column_names = [col[0] for col in edges_table_info]
    
    # Get nodes table schema to check for available columns
    nodes_table_info = db.sql("DESCRIBE nodes").fetchall()
    node_column_names = [col[0] for col in nodes_table_info]
    
    # Build edge joins with proper multivalued field handling
    edge_field_joins = []
    for field in edge_fields:
        is_multivalued = field in multivalued_fields and 'VARCHAR[]' in edges_table_types.get(field, '').upper()
        edge_field_joins.append(edge_joins(field, is_multivalued=is_multivalued))
    
    edge_field_to_label_joins = []
    for field in edge_fields_to_label:
        is_multivalued = field in multivalued_fields and 'VARCHAR[]' in edges_table_types.get(field, '').upper()
        edge_field_to_label_joins.append(edge_joins(field, include_closure_joins=False, is_multivalued=is_multivalued))

    # Identify columns that will be created by edge_columns() to avoid conflicts
    # These columns should be excluded from edges.* selection
    columns_to_exclude = set()
    for field in edge_fields + edge_fields_to_label:
        columns_to_exclude.add(f"{field}_label")
        columns_to_exclude.add(f"{field}_category")
        columns_to_exclude.add(f"{field}_namespace")
        columns_to_exclude.add(f"{field}_closure")
        columns_to_exclude.add(f"{field}_closure_label")
        columns_to_exclude.add(f"{field}_taxon")
        columns_to_exclude.add(f"{field}_taxon_label")

    # Build edges.* EXCLUDE clause to avoid column name conflicts
    excluded_columns_list = [col for col in columns_to_exclude if col in edges_column_names]
    if excluded_columns_list:
        edges_select = f"edges.* EXCLUDE ({', '.join(excluded_columns_list)})"
    else:
        edges_select = "edges.*"

    # Materialize per-edge derived columns onto `edges` itself: evidence_count
    # and grouping_key are computed from edges columns only, cheap to store,
    # and survive across re-runs / external queries on the base table.
    if not dry_run:
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

    # denormalized_edges is a VIEW: edges left-joined to node lookups + closure
    # tables for each configured field. No data duplication; the heavy
    # closure_id / closure_label tables stay materialized as before.
    # Drop any prior materialization (view OR table) before recreating.
    if not dry_run:
        _drop_any("denormalized_edges", db)
    edges_query = f"""
    create or replace view denormalized_edges as
    select {edges_select},
           {"".join([edge_columns(field, node_column_names=node_column_names) for field in edge_fields])}
           {"".join([edge_columns(field, include_closure_fields=False, node_column_names=node_column_names) for field in edge_fields_to_label])}
           edges.evidence_count,
           edges.grouping_key
    from edges
        {"".join(edge_field_joins)}
        {"".join(edge_field_to_label_joins)}
    """

    print(edges_query)

    # Map monarch-ingest's legacy `additional_node_constraints` (free-form WHERE
    # clause referencing `has_phenotype_edges`) to a per-predicate filter on
    # the base edges table. Today's only constraint filters out negated edges.
    per_predicate_filter: Optional[str] = None
    if additional_node_constraints:
        # The legacy form references `<field>_edges.negated`; rewrite to apply
        # against the base `edges` alias used in the side-table query.
        per_predicate_filter = additional_node_constraints
        for f in node_fields:
            field = f.replace("biolink:", "")
            per_predicate_filter = per_predicate_filter.replace(f"{field}_edges.", "e.")


    if not dry_run:

        db.sql(edges_query)

        # Export edges to TSV only if requested
        if export_edges:
            edge_closure_replacements = [
                f"""
                list_aggregate({field}_closure, 'string_agg', '|') as {field}_closure,
                list_aggregate({field}_closure_label, 'string_agg', '|') as {field}_closure_label
                """
                for field in edge_fields
            ]
            
            # Add conversions for original multivalued fields back to pipe-delimited strings
            edge_table_info = db.sql("DESCRIBE denormalized_edges").fetchall()
            edge_table_column_names = [col[0] for col in edge_table_info]
            edge_table_types = {col[0]: col[1] for col in edge_table_info}
            
            # Create set of closure fields already handled by edge_closure_replacements
            closure_fields_handled = set()
            for field in edge_fields:
                closure_fields_handled.add(f"{field}_closure")
                closure_fields_handled.add(f"{field}_closure_label")
            
            multivalued_replacements = [
                f"list_aggregate({field}, 'string_agg', '|') as {field}"
                for field in multivalued_fields 
                if field in edge_table_column_names and 'VARCHAR[]' in edge_table_types[field].upper()
                and field not in closure_fields_handled
            ]
            
            all_replacements = edge_closure_replacements + multivalued_replacements
            edge_closure_replacements = "REPLACE (\n" + ",\n".join(all_replacements) + ")\n"

            edges_export_query = f"""
            -- write denormalized_edges as tsv
            copy (select * {edge_closure_replacements} from denormalized_edges) to '{edges_output_file}' (header, delimiter '\t')
            """
            print(edges_export_query)
            db.sql(edges_export_query)

        # Build one side table per configured node predicate, each bounded
        # by that predicate's edge subset — no monolithic GROUP BY.
        side_table_joins = []
        side_table_columns = []
        for node_field in node_fields:
            field = node_field.replace("biolink:", "")
            side_table = build_node_predicate_side_table(db, node_field, per_predicate_filter)
            alias = f"_{field}"
            side_table_joins.append(f"LEFT JOIN {side_table} {alias} ON nodes.id = {alias}.id")
            for col in (field, f"{field}_label", f"{field}_count",
                        f"{field}_closure", f"{field}_closure_label"):
                side_table_columns.append(f"{alias}.{col}")

        # denormalized_nodes is a VIEW: nodes plus per-predicate side tables
        # plus descendants_id/_label. No data duplication; has_descendant_count
        # is computed at view-read time from the descendants array length.
        _drop_any("denormalized_nodes", db)
        nodes_view_query = f"""
        CREATE OR REPLACE VIEW denormalized_nodes AS
        SELECT
            nodes.*,
            {", ".join(side_table_columns) + "," if side_table_columns else ""}
            _d.descendants AS has_descendant,
            _dl.descendants_label AS has_descendant_label,
            COALESCE(ARRAY_LENGTH(_d.descendants), 0) AS has_descendant_count
        FROM nodes
        {chr(10).join(side_table_joins)}
        LEFT JOIN descendants_id _d ON nodes.id = _d.id
        LEFT JOIN descendants_label _dl ON nodes.id = _dl.id
        """
        print(nodes_view_query)
        db.sql(nodes_view_query)
        
        # Export nodes to TSV only if requested
        if export_nodes:
            # Get denormalized_nodes table info to handle array fields in export
            denorm_nodes_table_info = db.sql("DESCRIBE denormalized_nodes").fetchall()
            denorm_nodes_column_names = [col[0] for col in denorm_nodes_table_info]
            denorm_nodes_types = {col[0]: col[1] for col in denorm_nodes_table_info}
            
            # Find all VARCHAR[] fields that need conversion to pipe-delimited strings
            array_field_replacements = [
                f"list_aggregate({field}, 'string_agg', '|') as {field}"
                for field in denorm_nodes_column_names 
                if 'VARCHAR[]' in denorm_nodes_types[field].upper()
            ]
            
            # The descendants fields are already handled by the general VARCHAR[] logic above
            # No need to add them separately
            
            if array_field_replacements:
                nodes_replacements = "REPLACE (\n" + ",\n".join(array_field_replacements) + ")\n"
                nodes_export_query = f"""
                -- write denormalized_nodes as tsv
                copy (select * {nodes_replacements} from denormalized_nodes) to '{nodes_output_file}' (header, delimiter '\t')
                """
            else:
                nodes_export_query = f"""
                -- write denormalized_nodes as tsv
                copy (select * from denormalized_nodes) to '{nodes_output_file}' (header, delimiter '\t')
                """
            print(nodes_export_query)
            db.sql(nodes_export_query)
