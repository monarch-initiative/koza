"""
Connectivity and topology analysis using GRAPE/ensmallen.

Computes connected components and produces parquet sidecar tables:
  - cc_nodes.parquet        — node-to-component assignment
  - cc_components.parquet   — per-component summary stats
  - cc_component_sources.parquet — component x source x predicate edge counts

Requires: ensmallen (install via ``pip install koza[grape]``)

Pandas is used only at the ensmallen boundary (``_build_grape_graph`` and
``_register_components``); everything else is plain DuckDB SQL, matching the
rest of ``koza.graph_operations``.
"""

import time
from pathlib import Path

import yaml
from loguru import logger

from koza.model.graph_operations import (
    ComponentDetail,
    ComponentSizeDistribution,
    ConnectivityReportConfig,
    ConnectivityReportResult,
    ConnectivitySummary,
)

from .utils import GraphDatabase


def _check_ensmallen_available() -> bool:
    """Check whether ensmallen is importable."""
    try:
        from ensmallen import Graph  # noqa: F401

        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def _get_column_types(db: GraphDatabase, table_name: str) -> dict[str, str]:
    """Return mapping of column name to DuckDB data_type for *table_name*."""
    rows = db.conn.execute(
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = ?",
        [table_name],
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def _scalar_cast(col: str, col_type: str, alias: str | None = None) -> str:
    """Return a SQL expression rendering *col* as a scalar VARCHAR.

    Array-typed columns are collapsed into pipe-delimited strings so that
    ensmallen's ``Graph.from_pd`` (and our flat parquet sidecars) can consume
    them. Pass ``alias`` to qualify the column with a table alias (e.g.
    ``n`` → ``n."col"``).
    """
    qualified = f'{alias}."{col}"' if alias else f'"{col}"'
    if col_type.endswith("[]"):
        return f"array_to_string({qualified}, '|')"
    return qualified


# ---------------------------------------------------------------------------
# Ensmallen boundary — pandas is confined to this section
# ---------------------------------------------------------------------------


def _build_grape_graph(db: GraphDatabase, config: ConnectivityReportConfig):
    """Load a minimal nodes/edges slice and build an ensmallen ``Graph``.

    This is the only place pandas is used for graph construction, because
    ``Graph.from_pd`` requires pandas DataFrames. The DataFrames are dropped
    as soon as the graph is built.
    """
    from ensmallen import Graph

    node_types = _get_column_types(db, "nodes")
    edge_types = _get_column_types(db, "edges")

    def _aliased(col: str, types: dict[str, str]) -> str:
        return f'{_scalar_cast(col, types[col])} AS "{col}"'

    # --- nodes slice (only the columns ensmallen needs) --------------------
    node_select = [_aliased(config.node_name_column, node_types)]
    grape_node_cols = [config.node_name_column]
    grape_kwargs: dict = {"node_name_column": config.node_name_column}

    if config.node_type_column and config.node_type_column in node_types:
        node_select.append(_aliased(config.node_type_column, node_types))
        grape_node_cols.append(config.node_type_column)
        grape_kwargs["node_type_column"] = config.node_type_column

    if not config.quiet:
        print("Loading nodes...")
    nodes_df = db.conn.execute(f"SELECT {', '.join(node_select)} FROM nodes").df()
    if not config.quiet:
        print(f"  {len(nodes_df):,} nodes")

    # --- edges slice (only the columns ensmallen needs) --------------------
    edge_select = [
        _aliased(config.edge_src_column, edge_types),
        _aliased(config.edge_dst_column, edge_types),
    ]
    grape_edge_cols = [config.edge_src_column, config.edge_dst_column]
    if config.edge_type_column and config.edge_type_column in edge_types:
        edge_select.append(_aliased(config.edge_type_column, edge_types))
        grape_edge_cols.append(config.edge_type_column)
        grape_kwargs["edge_type_column"] = config.edge_type_column

    if not config.quiet:
        print("Loading edges...")
    edges_df = db.conn.execute(f"SELECT {', '.join(edge_select)} FROM edges").df()
    if not config.quiet:
        print(f"  {len(edges_df):,} edges")

    if not config.quiet:
        direction = "directed" if config.directed else "undirected"
        print(f"Building GRAPE graph ({direction} for connectivity analysis)...")

    graph = Graph.from_pd(
        directed=config.directed,
        edges_df=edges_df[grape_edge_cols],
        nodes_df=nodes_df[grape_node_cols],
        name=config.graph_name,
        **grape_kwargs,
    )

    if not config.quiet:
        print(f"  Graph: {graph.get_number_of_nodes():,} nodes, {graph.get_number_of_edges():,} edges")

    return graph


def _register_components(db: GraphDatabase, node_names: list[str], raw_ids: list[int]) -> None:
    """Bridge the ensmallen CC result into DuckDB as temp tables.

    Pandas is used here as a fast zero-config way to move a numpy array from
    ensmallen into DuckDB (``executemany`` is ~1000x slower for large graphs).
    The DataFrame is dropped immediately after registration.

    Creates two TEMP TABLEs:
      - ``node_components(node_id, component_id)`` — component_id ranked by
        descending size (LCC = 0).
      - ``component_sizes(component_id, component_size)``.
    """
    import pandas as pd

    df = pd.DataFrame({"node_id": node_names, "raw_component_id": raw_ids})
    db.conn.register("_raw_components_df", df)

    db.conn.execute(
        """
        CREATE TEMP TABLE _component_rank AS
        SELECT
            raw_component_id,
            CAST(ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC, raw_component_id) - 1 AS UINTEGER) AS component_id,
            CAST(COUNT(*) AS UINTEGER) AS component_size
        FROM _raw_components_df
        GROUP BY raw_component_id
        """
    )
    db.conn.execute(
        """
        CREATE TEMP TABLE node_components AS
        SELECT r.node_id, cr.component_id
        FROM _raw_components_df r
        JOIN _component_rank cr USING (raw_component_id)
        """
    )
    db.conn.execute(
        """
        CREATE TEMP TABLE component_sizes AS
        SELECT component_id, component_size FROM _component_rank
        """
    )

    db.conn.unregister("_raw_components_df")
    db.conn.execute("DROP TABLE _component_rank")
    del df


# ---------------------------------------------------------------------------
# Connected-component computation
# ---------------------------------------------------------------------------


def _compute_components(graph, quiet: bool = False) -> tuple[list[str], list[int], float]:
    """Run GRAPE's CC algorithm.

    Returns
    -------
    node_names : list of node name strings, indexed by ensmallen node id
    raw_ids    : raw component id per node (pre-ranking)
    elapsed    : computation time in seconds (rounded)
    """
    if not quiet:
        print("\nComputing connected components...")

    t0 = time.perf_counter()
    component_ids = graph.get_node_connected_component_ids(verbose=not quiet)
    elapsed = time.perf_counter() - t0

    if not quiet:
        print(f"  Completed in {elapsed:.2f}s")

    num_nodes = graph.get_number_of_nodes()
    node_names = [graph.get_node_name_from_node_id(i) for i in range(num_nodes)]
    raw_ids = [int(c) for c in component_ids]
    return node_names, raw_ids, round(elapsed, 2)


# ---------------------------------------------------------------------------
# Sidecar tables (pure DuckDB SQL)
# ---------------------------------------------------------------------------


def _size_bucket(size: int, lcc_size: int) -> str:
    """Assign a component to a human-readable size bucket.

    Kept as a pure Python helper for unit testing; the main pipeline performs
    bucketing in SQL inside ``_build_sidecar_tables``.
    """
    if size == lcc_size:
        return "LCC"
    if size >= 100:
        return "100+"
    if size >= 10:
        return "10-99"
    if size >= 2:
        return "2-9"
    return "Isolated"


def _build_sidecar_tables(
    db: GraphDatabase, config: ConnectivityReportConfig, quiet: bool = False
) -> None:
    """Create TEMP TABLEs ``cc_nodes``, ``cc_component_sources``, ``cc_components``.

    All transformations are performed in DuckDB SQL against the pre-existing
    ``nodes``/``edges`` tables plus the ``node_components`` / ``component_sizes``
    temp tables produced by ``_register_components``.
    """
    node_types = _get_column_types(db, "nodes")
    edge_types = _get_column_types(db, "edges")
    node_cols = set(node_types)
    edge_cols = set(edge_types)
    has_category = "category" in node_cols
    has_provided_by_nodes = "provided_by" in node_cols
    has_pks = "primary_knowledge_source" in edge_cols
    has_name = "name" in node_cols

    # ── 1. cc_nodes ─────────────────────────────────────────────────────────
    #
    # Every non-name column from the nodes table is carried over, with arrays
    # cast to pipe-delimited strings for a flat parquet layout.
    deprecated_expr = (
        "CASE WHEN n.\"name\" LIKE 'obsolete%' THEN TRUE ELSE FALSE END"
        if has_name
        else "FALSE"
    )
    extra_node_sql_parts: list[str] = [
        f'{_scalar_cast(col, node_types[col], alias="n")} AS "{col}"'
        for col in node_cols
        if col != config.node_name_column
    ]
    extras_joined = (", " + ", ".join(extra_node_sql_parts)) if extra_node_sql_parts else ""

    if not quiet:
        print("\nBuilding cc_nodes table...")

    db.conn.execute(
        f"""
        CREATE TEMP TABLE cc_nodes AS
        SELECT
            nc.node_id,
            nc.component_id{extras_joined},
            {deprecated_expr} AS deprecated
        FROM node_components nc
        LEFT JOIN nodes n ON n."{config.node_name_column}" = nc.node_id
        """
    )

    if not quiet:
        n_rows = db.conn.execute("SELECT COUNT(*) FROM cc_nodes").fetchone()[0]
        n_dep = (
            db.conn.execute(
                "SELECT SUM(CASE WHEN deprecated THEN 1 ELSE 0 END) FROM cc_nodes"
            ).fetchone()[0]
            or 0
        )
        print(f"  {n_rows:,} rows ({int(n_dep):,} deprecated)")

    # ── 2. cc_component_sources ─────────────────────────────────────────────
    #
    # Edges joined to their subject's component, grouped by component +
    # (predicate, primary_knowledge_source, provided_by) — whichever exist.
    # Components of size 1 (true singletons) are excluded.
    edge_group_cols: list[str] = [
        c for c in ("primary_knowledge_source", "provided_by", "predicate") if c in edge_cols
    ]
    edge_group_raw = [_scalar_cast(c, edge_types[c], alias="e") for c in edge_group_cols]
    edge_group_exprs = [f'{expr} AS "{col}"' for col, expr in zip(edge_group_cols, edge_group_raw, strict=True)]

    extras_edge_sql = (", " + ", ".join(edge_group_exprs)) if edge_group_exprs else ""
    group_by_sql = ", ".join(["nc.component_id", *edge_group_raw])

    if not quiet:
        print("Building cc_component_sources table...")

    db.conn.execute(
        f"""
        CREATE TEMP TABLE cc_component_sources AS
        SELECT
            nc.component_id{extras_edge_sql},
            CAST(COUNT(*) AS UINTEGER) AS edge_count
        FROM edges e
        JOIN node_components nc ON nc.node_id = e."{config.edge_src_column}"
        JOIN component_sizes cs ON cs.component_id = nc.component_id
        WHERE cs.component_size > 1
        GROUP BY {group_by_sql}
        """
    )

    if not quiet:
        n_rows = db.conn.execute("SELECT COUNT(*) FROM cc_component_sources").fetchone()[0]
        print(f"  {n_rows:,} rows")

    # ── 3. cc_components ────────────────────────────────────────────────────
    #
    # Per-component roll-up. All summary/print queries expect a stable set of
    # columns so we emit defaults (0 / NULL) when source data isn't available.
    node_agg_parts: list[str] = [
        "component_id",
        "CAST(COUNT(*) AS UINTEGER) AS component_size",
        "CAST(SUM(CASE WHEN deprecated THEN 1 ELSE 0 END) AS UINTEGER) AS num_deprecated",
    ]
    if has_category:
        node_agg_parts.extend(
            [
                "CAST(COUNT(DISTINCT category) AS UINTEGER) AS num_categories",
                "mode(category) AS top_category",
                "BOOL_OR(category = 'biolink:Disease') AS has_disease",
                "BOOL_OR(category = 'biolink:Gene') AS has_gene",
            ]
        )
    else:
        node_agg_parts.extend(
            [
                "CAST(0 AS UINTEGER) AS num_categories",
                "CAST(NULL AS VARCHAR) AS top_category",
            ]
        )
    if has_provided_by_nodes:
        node_agg_parts.append("CAST(COUNT(DISTINCT provided_by) AS UINTEGER) AS num_provided_by")
    node_agg_parts.append("array_to_string(list(node_id)[1:5], '|') AS sample_node_ids")

    ctes = [
        f"node_agg AS (SELECT {', '.join(node_agg_parts)} FROM cc_nodes GROUP BY component_id)",
        (
            "edge_agg AS (SELECT component_id, "
            "CAST(SUM(edge_count) AS UINTEGER) AS num_edges "
            "FROM cc_component_sources GROUP BY component_id)"
        ),
    ]
    if has_pks:
        ctes.append(
            "ks AS (SELECT component_id, "
            "CAST(COUNT(DISTINCT primary_knowledge_source) AS UINTEGER) AS num_knowledge_sources "
            "FROM cc_component_sources GROUP BY component_id)"
        )

    select_parts: list[str] = [
        "na.*",
        "COALESCE(ea.num_edges, CAST(0 AS UINTEGER)) AS num_edges",
    ]
    if has_pks:
        select_parts.append(
            "COALESCE(ks.num_knowledge_sources, CAST(0 AS UINTEGER)) AS num_knowledge_sources"
        )
    else:
        select_parts.append("CAST(0 AS UINTEGER) AS num_knowledge_sources")

    lcc_size = (
        db.conn.execute("SELECT MAX(component_size) FROM component_sizes").fetchone()[0] or 0
    )
    select_parts.append(
        f"""CASE
            WHEN na.component_size = {int(lcc_size)} THEN 'LCC'
            WHEN na.component_size >= 100 THEN '100+'
            WHEN na.component_size >= 10 THEN '10-99'
            WHEN na.component_size >= 2 THEN '2-9'
            ELSE 'Isolated'
        END AS size_bucket"""
    )

    ks_join = "LEFT JOIN ks ON ks.component_id = na.component_id" if has_pks else ""

    if not quiet:
        print("Building cc_components table...")

    db.conn.execute(
        f"""
        CREATE TEMP TABLE cc_components AS
        WITH {', '.join(ctes)}
        SELECT {', '.join(select_parts)}
        FROM node_agg na
        LEFT JOIN edge_agg ea ON ea.component_id = na.component_id
        {ks_join}
        ORDER BY na.component_id
        """
    )

    if not quiet:
        n_rows = db.conn.execute("SELECT COUNT(*) FROM cc_components").fetchone()[0]
        print(f"  {n_rows:,} rows")


def _write_parquet_sidecars(
    db: GraphDatabase,
    output_dir: Path,
    quiet: bool = False,
) -> dict[str, Path]:
    """Write the three sidecar tables to parquet via DuckDB's native writer."""
    output_dir.mkdir(parents=True, exist_ok=True)

    files: dict[str, Path] = {}
    for name in ("cc_nodes", "cc_components", "cc_component_sources"):
        path = output_dir / f"{name}.parquet"
        # DuckDB COPY handles parquet natively — no pandas/pyarrow on this path.
        db.conn.execute(
            f"COPY (SELECT * FROM {name}) TO '{path}' (FORMAT PARQUET)"
        )
        files[name] = path

    if not quiet:
        print(f"\nParquet files written to {output_dir}/:")
        for name, path in files.items():
            n = db.conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            print(f"  {path.name:<35} {n:>10,} rows")

    return files


# ---------------------------------------------------------------------------
# Summary construction
# ---------------------------------------------------------------------------


def _build_connectivity_summary(
    db: GraphDatabase,
    graph,
    config: ConnectivityReportConfig,
) -> ConnectivitySummary:
    """Construct a ``ConnectivitySummary`` from the DuckDB sidecar tables.

    Node and edge counts are sourced from DuckDB, not GRAPE. GRAPE collapses
    edges to its topological skeleton (unique unordered SO-pairs in undirected
    mode, or unique SPO triples if an edge_type_column is passed), which is an
    implementation detail of CC. The property-graph row counts are what users
    care about.
    """
    num_nodes = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    num_edges = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

    comp_row = db.conn.execute(
        """
        SELECT
            COUNT(*),
            MAX(component_size),
            SUM(CASE WHEN component_size = 1 THEN 1 ELSE 0 END)
        FROM component_sizes
        """
    ).fetchone()
    num_components = int(comp_row[0])
    lcc_size = int(comp_row[1] or 0)
    num_singletons = int(comp_row[2] or 0)

    lcc_fraction = lcc_size / num_nodes if num_nodes > 0 else 0.0

    total_deprecated = int(
        db.conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN deprecated THEN 1 ELSE 0 END), 0) FROM cc_nodes"
        ).fetchone()[0]
    )

    bucket_rows = db.conn.execute(
        """
        SELECT size_bucket, COUNT(*), CAST(SUM(component_size) AS BIGINT)
        FROM cc_components
        GROUP BY size_bucket
        """
    ).fetchall()
    bucket_map = {r[0]: (int(r[1]), int(r[2])) for r in bucket_rows}
    size_dist = [
        ComponentSizeDistribution(
            bucket=b, num_components=bucket_map[b][0], total_nodes=bucket_map[b][1]
        )
        for b in ("LCC", "100+", "10-99", "2-9", "Isolated")
        if b in bucket_map
    ]

    top_minor_rows = db.conn.execute(
        """
        SELECT component_id, component_size, num_edges, top_category,
               num_categories, num_knowledge_sources, sample_node_ids
        FROM cc_components
        WHERE component_id > 0
        ORDER BY component_id
        LIMIT ?
        """,
        [int(config.top_components)],
    ).fetchall()
    top_minor = [
        ComponentDetail(
            component_id=int(r[0]),
            component_size=int(r[1]),
            num_edges=int(r[2] or 0),
            top_category=r[3],
            num_categories=int(r[4] or 0),
            num_knowledge_sources=int(r[5] or 0),
            sample_node_ids=(r[6].split("|") if r[6] else []),
        )
        for r in top_minor_rows
    ]

    return ConnectivitySummary(
        graph_name=config.graph_name,
        num_nodes=num_nodes,
        num_edges=num_edges,
        directed=graph.is_directed(),
        num_components=num_components,
        lcc_size=lcc_size,
        lcc_fraction=round(lcc_fraction, 6),
        num_singletons=num_singletons,
        num_non_singleton_components=num_components - num_singletons,
        nodes_outside_lcc=num_nodes - lcc_size,
        total_deprecated=total_deprecated,
        size_distribution=size_dist,
        top_minor_components=top_minor,
    )


# ---------------------------------------------------------------------------
# Console report
# ---------------------------------------------------------------------------


def _print_connectivity_report(
    db: GraphDatabase,
    summary: ConnectivitySummary,
    has_category: bool,
    has_pks: bool,
    elapsed: float,
) -> None:
    """Print a structured console report.

    All tabular slices come from DuckDB SQL against the temp sidecar tables.
    """
    print("\n" + "=" * 70)
    print(f"  CONNECTED COMPONENT REPORT: {summary.graph_name}")
    print("=" * 70)

    print(f"\n  Graph: {summary.num_nodes:,} nodes, {summary.num_edges:,} edges")
    print(f"  Directed: {summary.directed}")

    print("\n--- Overview ---")
    print(f"  Connected components:       {summary.num_components:,}")
    print(f"  LCC size:                   {summary.lcc_size:,} ({summary.lcc_fraction:.2%} of all nodes)")
    print(f"  Disconnected fragments:     {summary.num_components - 1:,}")
    print(f"  Singleton (isolated) nodes: {summary.num_singletons:,}")
    print(f"  Non-singleton components:   {summary.num_non_singleton_components:,}")
    print(f"  Nodes outside LCC:          {summary.nodes_outside_lcc:,}")

    if summary.total_deprecated > 0:
        dep_in_lcc = int(
            db.conn.execute(
                "SELECT COUNT(*) FROM cc_nodes WHERE component_id = 0 AND deprecated"
            ).fetchone()[0]
        )
        dep_singleton = int(
            db.conn.execute(
                """
                SELECT COUNT(*)
                FROM cc_nodes cn
                JOIN component_sizes cs ON cs.component_id = cn.component_id
                WHERE cn.deprecated AND cs.component_size = 1
                """
            ).fetchone()[0]
        )
        print("\n--- Deprecated (obsolete) Nodes ---")
        print(f"  Total deprecated:           {summary.total_deprecated:,}")
        print(f"    in LCC:                   {dep_in_lcc:,}")
        print(f"    singletons:               {dep_singleton:,}")
        print(f"    minor components:         {summary.total_deprecated - dep_in_lcc - dep_singleton:,}")

    print("\n--- Component Size Distribution ---")
    print(f"  {'Bucket':<16} {'Components':>12} {'Total Nodes':>14}")
    print(f"  {'-' * 16} {'-' * 12} {'-' * 14}")
    for dist in summary.size_distribution:
        print(f"  {dist.bucket:<16} {dist.num_components:>12,} {dist.total_nodes:>14,}")

    if has_category:
        print("\n--- Top Categories in LCC (top 20) ---")
        lcc_cats = db.conn.execute(
            """
            SELECT category, COUNT(*)
            FROM cc_nodes
            WHERE component_id = 0 AND category IS NOT NULL
            GROUP BY category
            ORDER BY COUNT(*) DESC
            LIMIT 20
            """
        ).fetchall()
        for cat, count in lcc_cats:
            print(f"  {cat:<45} {count:>10,}")

        print("\n--- Top Categories Outside LCC (top 20) ---")
        non_lcc_cats = db.conn.execute(
            """
            SELECT category, COUNT(*)
            FROM cc_nodes
            WHERE component_id != 0 AND category IS NOT NULL
            GROUP BY category
            ORDER BY COUNT(*) DESC
            LIMIT 20
            """
        ).fetchall()
        for cat, count in non_lcc_cats:
            print(f"  {cat:<45} {count:>10,}")

    if summary.top_minor_components:
        print("\n--- Top Minor Components (excluding LCC) ---")
        for comp in summary.top_minor_components:
            cat_info = (
                f"top: {comp.top_category} ({comp.num_categories} categories)"
                if comp.top_category
                else ""
            )
            print(f"  Component {comp.component_id:>5}: {comp.component_size:>8,} nodes | {cat_info}")
            if comp.sample_node_ids:
                print(f"    Sample: {', '.join(comp.sample_node_ids[:5])}")

    if has_pks:
        minor_src = db.conn.execute(
            """
            SELECT primary_knowledge_source, SUM(edge_count)
            FROM cc_component_sources
            WHERE component_id != 0 AND primary_knowledge_source IS NOT NULL
            GROUP BY primary_knowledge_source
            ORDER BY SUM(edge_count) DESC
            LIMIT 15
            """
        ).fetchall()
        if minor_src:
            print("\n--- Top Knowledge Sources in Minor Components (by edge count) ---")
            for src, count in minor_src:
                print(f"  {src:<50} {int(count):>10,}")

    print(f"\n  Computed in {elapsed:.2f}s")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def generate_connectivity_report(config: ConnectivityReportConfig) -> ConnectivityReportResult:
    """
    Generate a connectivity/topology report for a KGX DuckDB database.

    Computes connected components using GRAPE/ensmallen and produces parquet
    sidecar tables with component assignments and summary statistics.

    Requires ensmallen: ``pip install koza[grape]``

    Args:
        config: ConnectivityReportConfig with database path and options.

    Returns:
        ConnectivityReportResult with summary and file paths.

    Raises:
        ImportError: If ensmallen is not installed.
        FileNotFoundError: If database does not exist.
    """
    start_time = time.time()

    try:
        if not _check_ensmallen_available():
            raise ImportError(
                "The connectivity report requires ensmallen. "
                "Install it with: pip install koza[grape]"
            )

        if not config.database_path.exists():
            raise FileNotFoundError(f"Database not found: {config.database_path}")

        with GraphDatabase(config.database_path, read_only=True) as db:
            if not config.quiet:
                print(f"Generating connectivity report for {config.database_path.name}...")

            node_types = _get_column_types(db, "nodes")
            edge_types = _get_column_types(db, "edges")
            has_category = "category" in node_types
            has_pks = "primary_knowledge_source" in edge_types

            # 1. Build GRAPE graph (pandas slice #1)
            graph = _build_grape_graph(db, config)

            # 2. Compute connected components
            node_names, raw_ids, cc_elapsed = _compute_components(graph, quiet=config.quiet)

            # 3. Bridge CC result into DuckDB (pandas slice #2 — ensmallen boundary)
            _register_components(db, node_names, raw_ids)

            # 4. Build sidecar tables in pure SQL
            _build_sidecar_tables(db, config, quiet=config.quiet)

            # 5. Write parquet sidecars via DuckDB's native writer
            parquet_files: dict[str, Path] = {}
            if config.output_dir:
                parquet_files = _write_parquet_sidecars(
                    db, config.output_dir, quiet=config.quiet
                )

            # 6. Build summary from SQL queries against the sidecar tables
            summary = _build_connectivity_summary(db, graph, config)

            # 7. Write YAML summary
            if config.output_file:
                config.output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(config.output_file, "w") as f:
                    yaml.dump(summary.model_dump(), f, default_flow_style=False, sort_keys=False)
                if not config.quiet:
                    print(f"\nYAML summary written to {config.output_file}")

            # 8. Console report
            if not config.quiet:
                _print_connectivity_report(db, summary, has_category, has_pks, cc_elapsed)

            total_time = time.time() - start_time

            return ConnectivityReportResult(
                summary=summary,
                output_dir=config.output_dir,
                output_file=config.output_file,
                parquet_files=parquet_files,
                computation_seconds=cc_elapsed,
                total_time_seconds=total_time,
            )

    except Exception as e:
        logger.error(f"Connectivity report generation failed: {e}")

        if not config.quiet:
            print(f"Connectivity report generation failed: {e}")

        raise
