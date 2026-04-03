"""
Connectivity and topology analysis using GRAPE/ensmallen.

Computes connected components and produces parquet sidecar tables:
  - cc_nodes.parquet        — node-to-component assignment
  - cc_components.parquet   — per-component summary stats
  - cc_component_sources.parquet — component x source x predicate edge counts

Requires: ensmallen (install via ``pip install koza[grape]``)
"""

import time
from pathlib import Path

import pandas as pd
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
# Graph loading
# ---------------------------------------------------------------------------


def _get_available_columns(db: GraphDatabase, table_name: str) -> set[str]:
    """Return the set of column names present in *table_name*."""
    rows = db.conn.execute(
        f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'"
    ).fetchall()
    return {r[0] for r in rows}


def _cast_array_columns_to_varchar(df: pd.DataFrame) -> pd.DataFrame:
    """Cast any list/array columns to pipe-delimited VARCHAR strings.

    GRAPE's ``Graph.from_pd`` expects simple scalar columns.  KGX databases
    produced by Koza's join operation store multivalued fields (e.g. category,
    provided_by) as ``VARCHAR[]``.  DuckDB surfaces these as Python lists in
    the pandas DataFrame, which GRAPE cannot handle.
    """
    for col in df.columns:
        if df[col].dtype == object and len(df) > 0:
            sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            if isinstance(sample, list):
                df[col] = df[col].apply(lambda v: "|".join(str(x) for x in v) if isinstance(v, list) else v)
    return df


def _load_grape_graph(
    db: GraphDatabase,
    config: ConnectivityReportConfig,
) -> tuple:
    """Load nodes/edges from DuckDB, build a GRAPE graph, return wide DataFrames.

    Returns
    -------
    graph : ensmallen.Graph
    nodes_wide : pd.DataFrame   (all available node columns)
    edges_wide : pd.DataFrame   (all available edge columns)
    """
    from ensmallen import Graph

    node_cols = _get_available_columns(db, "nodes")
    edge_cols = _get_available_columns(db, "edges")

    # -- nodes: always need the name column; grab everything useful --------
    want_node_cols = [config.node_name_column]
    for col in ["name", "category", "provided_by", "in_taxon"]:
        if col in node_cols and col not in want_node_cols:
            want_node_cols.append(col)
    # Add any remaining columns that exist (for richer sidecar tables)
    select_node = ", ".join(want_node_cols)

    if not config.quiet:
        print("Loading nodes...")
    nodes_wide = db.conn.execute(f"SELECT {select_node} FROM nodes").df()
    nodes_wide = _cast_array_columns_to_varchar(nodes_wide)
    if not config.quiet:
        print(f"  {len(nodes_wide):,} nodes")

    # -- edges: always need src/dst; grab useful metadata ------------------
    want_edge_cols = [config.edge_src_column, config.edge_dst_column]
    for col in ["predicate", "primary_knowledge_source", "provided_by"]:
        if col in edge_cols and col not in want_edge_cols:
            want_edge_cols.append(col)
    select_edge = ", ".join(want_edge_cols)

    if not config.quiet:
        print("Loading edges...")
    edges_wide = db.conn.execute(f"SELECT {select_edge} FROM edges").df()
    edges_wide = _cast_array_columns_to_varchar(edges_wide)
    if not config.quiet:
        print(f"  {len(edges_wide):,} edges")

    # -- Build GRAPE graph -------------------------------------------------
    grape_node_cols = [config.node_name_column]
    grape_kwargs: dict = {
        "node_name_column": config.node_name_column,
    }
    if config.node_type_column and config.node_type_column in nodes_wide.columns:
        grape_node_cols.append(config.node_type_column)
        grape_kwargs["node_type_column"] = config.node_type_column

    grape_edge_cols = [config.edge_src_column, config.edge_dst_column]
    if config.edge_type_column and config.edge_type_column in edges_wide.columns:
        grape_edge_cols.append(config.edge_type_column)
        grape_kwargs["edge_type_column"] = config.edge_type_column

    if not config.quiet:
        direction = "directed" if config.directed else "undirected"
        print(f"Building GRAPE graph ({direction} for connectivity analysis)...")

    graph = Graph.from_pd(
        directed=config.directed,
        edges_df=edges_wide[grape_edge_cols],
        nodes_df=nodes_wide[grape_node_cols],
        name=config.graph_name,
        **grape_kwargs,
    )

    if not config.quiet:
        print(f"  Graph: {graph.get_number_of_nodes():,} nodes, {graph.get_number_of_edges():,} edges")

    return graph, nodes_wide, edges_wide


# ---------------------------------------------------------------------------
# Connected-component computation
# ---------------------------------------------------------------------------


def _compute_components(graph, quiet: bool = False) -> tuple[pd.DataFrame, float]:
    """Run GRAPE's connected-component algorithm.

    Returns
    -------
    node_components : DataFrame with columns ``[node_id, component_id]``
        ``component_id`` 0 is the LCC (ranked by descending size).
    elapsed : computation time in seconds
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

    node_components = pd.DataFrame(
        {
            "node_id": node_names,
            "raw_component_id": [int(c) for c in component_ids],
        }
    )

    # Rank by descending size so LCC = 0
    size_counts = node_components["raw_component_id"].value_counts()
    ranked_ids = {old_id: rank for rank, old_id in enumerate(size_counts.index)}
    node_components["component_id"] = node_components["raw_component_id"].map(ranked_ids).astype("uint32")
    node_components = node_components.drop(columns=["raw_component_id"])

    return node_components, round(elapsed, 2)


# ---------------------------------------------------------------------------
# Parquet sidecar tables
# ---------------------------------------------------------------------------


def _size_bucket(size: int, lcc_size: int) -> str:
    """Assign a component to a human-readable size bucket."""
    if size == lcc_size:
        return "LCC"
    if size >= 100:
        return "100+"
    if size >= 10:
        return "10-99"
    if size >= 2:
        return "2-9"
    return "Isolated"


def _build_parquet_tables(
    graph,
    nodes_wide: pd.DataFrame,
    edges_wide: pd.DataFrame,
    node_components: pd.DataFrame,
    config: ConnectivityReportConfig,
    quiet: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build the three sidecar DataFrames from the CC result.

    Returns ``(cc_nodes, cc_components, cc_component_sources)``.
    """
    # ── 1. cc_nodes ──────────────────────────────────────────────────────
    if not quiet:
        print("\nBuilding cc_nodes table...")

    cc_nodes = node_components.merge(
        nodes_wide.rename(columns={config.node_name_column: "node_id"}),
        on="node_id",
        how="left",
    )

    # Put node_id and component_id first, then everything else
    front_cols = ["node_id", "component_id"]
    rest = [c for c in cc_nodes.columns if c not in front_cols]
    cc_nodes = cc_nodes[front_cols + rest]

    # Mark deprecated/obsolete nodes if name column is available
    if "name" in cc_nodes.columns:
        cc_nodes["deprecated"] = cc_nodes["name"].str.startswith("obsolete", na=False)
    else:
        cc_nodes["deprecated"] = False

    if not quiet:
        print(f"  {len(cc_nodes):,} rows ({cc_nodes['deprecated'].sum():,} deprecated)")

    # ── 2. cc_component_sources ──────────────────────────────────────────
    if not quiet:
        print("Building cc_component_sources table...")

    subject_comp = node_components.rename(columns={"node_id": config.edge_src_column})
    edges_with_comp = edges_wide.merge(subject_comp, on=config.edge_src_column, how="inner")

    # Group-by columns: always component_id + predicate; add source cols if available
    groupby_cols = ["component_id"]
    if "primary_knowledge_source" in edges_with_comp.columns:
        groupby_cols.append("primary_knowledge_source")
    if "provided_by" in edges_with_comp.columns:
        groupby_cols.append("provided_by")
    if "predicate" in edges_with_comp.columns:
        groupby_cols.append("predicate")

    cc_component_sources = (
        edges_with_comp.groupby(groupby_cols, dropna=False).size().reset_index(name="edge_count")
    )
    cc_component_sources["edge_count"] = cc_component_sources["edge_count"].astype("uint32")
    cc_component_sources["component_id"] = cc_component_sources["component_id"].astype("uint32")

    # Exclude singletons (they have 0 internal edges)
    singleton_components = cc_nodes.groupby("component_id").size().reset_index(name="n")
    singleton_ids = set(singleton_components.loc[singleton_components["n"] == 1, "component_id"])
    cc_component_sources = cc_component_sources[
        ~cc_component_sources["component_id"].isin(singleton_ids)
    ].reset_index(drop=True)

    if not quiet:
        print(f"  {len(cc_component_sources):,} rows")

    # ── 3. cc_components ─────────────────────────────────────────────────
    if not quiet:
        print("Building cc_components table...")

    agg_dict: dict = {
        "component_size": ("node_id", "size"),
        "num_deprecated": ("deprecated", "sum"),
    }
    if "category" in cc_nodes.columns:
        agg_dict["num_categories"] = ("category", "nunique")
        agg_dict["top_category"] = ("category", lambda x: x.value_counts().index[0] if len(x) > 0 else None)
        agg_dict["has_disease"] = ("category", lambda x: (x == "biolink:Disease").any())
        agg_dict["has_gene"] = ("category", lambda x: (x == "biolink:Gene").any())
    if "provided_by" in cc_nodes.columns:
        agg_dict["num_provided_by"] = ("provided_by", "nunique")

    comp_agg = cc_nodes.groupby("component_id").agg(**agg_dict).reset_index()

    # Edge counts per component
    edge_counts = (
        cc_component_sources.groupby("component_id")["edge_count"].sum().reset_index().rename(columns={"edge_count": "num_edges"})
    )
    comp_agg = comp_agg.merge(edge_counts, on="component_id", how="left")
    comp_agg["num_edges"] = comp_agg["num_edges"].fillna(0).astype("uint32")

    # Knowledge source count per component
    if "primary_knowledge_source" in cc_component_sources.columns:
        ks_counts = (
            cc_component_sources.groupby("component_id")["primary_knowledge_source"]
            .nunique()
            .reset_index()
            .rename(columns={"primary_knowledge_source": "num_knowledge_sources"})
        )
        comp_agg = comp_agg.merge(ks_counts, on="component_id", how="left")
        comp_agg["num_knowledge_sources"] = comp_agg["num_knowledge_sources"].fillna(0).astype("uint16")

    # Size bucket
    lcc_size = int(comp_agg.loc[comp_agg["component_id"] == 0, "component_size"].iloc[0])
    comp_agg["size_bucket"] = comp_agg["component_size"].apply(lambda s: _size_bucket(int(s), lcc_size))

    # Sample node IDs (up to 5, pipe-delimited)
    sample_nodes = (
        cc_nodes.groupby("component_id")["node_id"]
        .apply(lambda x: "|".join(x.head(5)))
        .reset_index()
        .rename(columns={"node_id": "sample_node_ids"})
    )
    comp_agg = comp_agg.merge(sample_nodes, on="component_id", how="left")

    # Sort and finalize types
    cc_components = comp_agg.sort_values("component_id").reset_index(drop=True)
    cc_components["component_id"] = cc_components["component_id"].astype("uint32")
    cc_components["component_size"] = cc_components["component_size"].astype("uint32")
    cc_components["num_deprecated"] = cc_components["num_deprecated"].astype("uint32")

    if not quiet:
        print(f"  {len(cc_components):,} rows")

    return cc_nodes, cc_components, cc_component_sources


def _write_parquet_sidecars(
    cc_nodes: pd.DataFrame,
    cc_components: pd.DataFrame,
    cc_component_sources: pd.DataFrame,
    output_dir: Path,
    quiet: bool = False,
) -> dict[str, Path]:
    """Write the three parquet sidecar files. Returns name→path mapping."""
    output_dir.mkdir(parents=True, exist_ok=True)

    files: dict[str, Path] = {}
    for name, df in [
        ("cc_nodes", cc_nodes),
        ("cc_components", cc_components),
        ("cc_component_sources", cc_component_sources),
    ]:
        path = output_dir / f"{name}.parquet"
        df.to_parquet(path, index=False)
        files[name] = path

    if not quiet:
        print(f"\nParquet files written to {output_dir}/:")
        for name, path in files.items():
            df = {"cc_nodes": cc_nodes, "cc_components": cc_components, "cc_component_sources": cc_component_sources}[
                name
            ]
            print(f"  {path.name:<35} {len(df):>10,} rows")

    return files


# ---------------------------------------------------------------------------
# Summary construction
# ---------------------------------------------------------------------------


def _build_connectivity_summary(
    graph,
    cc_nodes: pd.DataFrame,
    cc_components: pd.DataFrame,
    config: ConnectivityReportConfig,
) -> ConnectivitySummary:
    """Construct a ``ConnectivitySummary`` from the computed DataFrames."""
    num_nodes = graph.get_number_of_nodes()
    num_components = len(cc_components)
    lcc_size = int(cc_components.iloc[0]["component_size"])
    lcc_fraction = lcc_size / num_nodes if num_nodes > 0 else 0.0
    num_singletons = int((cc_components["component_size"] == 1).sum())

    # Size distribution
    bucket_order = ["LCC", "100+", "10-99", "2-9", "Isolated"]
    bucket_stats = cc_components.groupby("size_bucket").agg(
        num_components=("component_id", "size"),
        total_nodes=("component_size", "sum"),
    )
    size_dist = []
    for b in bucket_order:
        if b in bucket_stats.index:
            row = bucket_stats.loc[b]
            size_dist.append(
                ComponentSizeDistribution(
                    bucket=b,
                    num_components=int(row["num_components"]),
                    total_nodes=int(row["total_nodes"]),
                )
            )

    # Top minor components
    top_minor = []
    for _, comp in cc_components.iloc[1 : config.top_components + 1].iterrows():
        detail = ComponentDetail(
            component_id=int(comp["component_id"]),
            component_size=int(comp["component_size"]),
            num_edges=int(comp.get("num_edges", 0)),
            top_category=comp.get("top_category"),
            num_categories=int(comp["num_categories"]) if "num_categories" in comp.index else 0,
            num_knowledge_sources=int(comp["num_knowledge_sources"]) if "num_knowledge_sources" in comp.index else 0,
            sample_node_ids=comp["sample_node_ids"].split("|") if comp.get("sample_node_ids") else [],
        )
        top_minor.append(detail)

    total_deprecated = int(cc_nodes["deprecated"].sum()) if "deprecated" in cc_nodes.columns else 0

    return ConnectivitySummary(
        graph_name=config.graph_name,
        num_nodes=num_nodes,
        num_edges=graph.get_number_of_edges(),
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
    summary: ConnectivitySummary,
    cc_nodes: pd.DataFrame,
    cc_components: pd.DataFrame,
    cc_component_sources: pd.DataFrame,
    elapsed: float,
) -> None:
    """Print a structured console report."""
    print("\n" + "=" * 70)
    print(f"  CONNECTED COMPONENT REPORT: {summary.graph_name}")
    print("=" * 70)

    print(f"\n  Graph: {summary.num_nodes:,} nodes, {summary.num_edges:,} edges")
    print(f"  Directed: {summary.directed}")

    print(f"\n--- Overview ---")
    print(f"  Connected components:       {summary.num_components:,}")
    print(f"  LCC size:                   {summary.lcc_size:,} ({summary.lcc_fraction:.2%} of all nodes)")
    print(f"  Disconnected fragments:     {summary.num_components - 1:,}")
    print(f"  Singleton (isolated) nodes: {summary.num_singletons:,}")
    print(f"  Non-singleton components:   {summary.num_non_singleton_components:,}")
    print(f"  Nodes outside LCC:          {summary.nodes_outside_lcc:,}")

    # Deprecated nodes
    if summary.total_deprecated > 0:
        dep_in_lcc = int(cc_nodes.loc[cc_nodes["component_id"] == 0, "deprecated"].sum())
        dep_singleton = int(
            cc_nodes.loc[
                cc_nodes["component_id"].isin(
                    cc_components.loc[cc_components["component_size"] == 1, "component_id"]
                ),
                "deprecated",
            ].sum()
        )
        print(f"\n--- Deprecated (obsolete) Nodes ---")
        print(f"  Total deprecated:           {summary.total_deprecated:,}")
        print(f"    in LCC:                   {dep_in_lcc:,}")
        print(f"    singletons:               {dep_singleton:,}")
        print(f"    minor components:         {summary.total_deprecated - dep_in_lcc - dep_singleton:,}")

    # Size distribution
    print(f"\n--- Component Size Distribution ---")
    print(f"  {'Bucket':<16} {'Components':>12} {'Total Nodes':>14}")
    print(f"  {'-' * 16} {'-' * 12} {'-' * 14}")
    for dist in summary.size_distribution:
        print(f"  {dist.bucket:<16} {dist.num_components:>12,} {dist.total_nodes:>14,}")

    # Category breakdown if available
    if "category" in cc_nodes.columns:
        print(f"\n--- Top Categories in LCC (top 20) ---")
        lcc_cats = cc_nodes.loc[cc_nodes["component_id"] == 0, "category"].value_counts().head(20)
        for cat, count in lcc_cats.items():
            print(f"  {cat:<45} {count:>10,}")

        print(f"\n--- Top Categories Outside LCC (top 20) ---")
        non_lcc_cats = cc_nodes.loc[cc_nodes["component_id"] != 0, "category"].value_counts().head(20)
        for cat, count in non_lcc_cats.items():
            print(f"  {cat:<45} {count:>10,}")

    # Top minor components
    if summary.top_minor_components:
        print(f"\n--- Top Minor Components (excluding LCC) ---")
        for comp in summary.top_minor_components:
            cat_info = f"top: {comp.top_category} ({comp.num_categories} categories)" if comp.top_category else ""
            print(f"  Component {comp.component_id:>5}: {comp.component_size:>8,} nodes | {cat_info}")
            if comp.sample_node_ids:
                print(f"    Sample: {', '.join(comp.sample_node_ids[:5])}")

    # Top knowledge sources in minor components
    if "primary_knowledge_source" in cc_component_sources.columns and len(cc_component_sources) > 0:
        minor_sources = (
            cc_component_sources[cc_component_sources["component_id"] != 0]
            .groupby("primary_knowledge_source")["edge_count"]
            .sum()
            .sort_values(ascending=False)
            .head(15)
        )
        if len(minor_sources) > 0:
            print(f"\n--- Top Knowledge Sources in Minor Components (by edge count) ---")
            for src, count in minor_sources.items():
                print(f"  {src:<50} {int(count):>10,}")

    print(f"\n  Computed in {elapsed:.2f}s")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def generate_connectivity_report(config: ConnectivityReportConfig) -> ConnectivityReportResult:
    """
    Generate a connectivity/topology report for a KGX DuckDB database.

    Computes connected components using GRAPE/ensmallen and produces
    parquet sidecar tables with component assignments and summary statistics.

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

        # 1. Load GRAPE graph
        graph, nodes_wide, edges_wide = _load_grape_graph(db, config)

        # 2. Compute connected components
        node_components, cc_elapsed = _compute_components(graph, quiet=config.quiet)

        # 3. Build parquet tables
        cc_nodes, cc_components, cc_component_sources = _build_parquet_tables(
            graph, nodes_wide, edges_wide, node_components, config, quiet=config.quiet
        )

        # 4. Build summary
        summary = _build_connectivity_summary(graph, cc_nodes, cc_components, config)

        # 5. Write parquet sidecars
        parquet_files: dict[str, Path] = {}
        if config.output_dir:
            parquet_files = _write_parquet_sidecars(
                cc_nodes, cc_components, cc_component_sources, config.output_dir, quiet=config.quiet
            )

        # 6. Write YAML summary
        if config.output_file:
            config.output_file.parent.mkdir(parents=True, exist_ok=True)
            report_dict = summary.model_dump()
            with open(config.output_file, "w") as f:
                yaml.dump(report_dict, f, default_flow_style=False, sort_keys=False)
            if not config.quiet:
                print(f"\nYAML summary written to {config.output_file}")

        # 7. Console report
        if not config.quiet:
            _print_connectivity_report(summary, cc_nodes, cc_components, cc_component_sources, cc_elapsed)

        total_time = time.time() - start_time

        return ConnectivityReportResult(
            summary=summary,
            output_dir=config.output_dir,
            output_file=config.output_file,
            parquet_files=parquet_files,
            computation_seconds=cc_elapsed,
            total_time_seconds=total_time,
        )
