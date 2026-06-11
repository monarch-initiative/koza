"""Load operation: faithfully ingest KGX node/edge files into a DuckDB.

`load` is the first step of a build on its own — get a knowledge graph that is
already represented as node and edge files into `nodes` / `edges` tables, ready
for analysis or downstream operations (`closurize`, `report`, ...), without the
deduplicate / normalize / prune stages that `merge` runs.

Mechanically it is `join` with faithful-load defaults (preserve `provided_by`
instead of stamping it from the source filename, and skip the schema report),
so this module is a thin, intent-revealing wrapper over `join_graphs`. The
distinction is semantic: `join`/`merge` build a graph from raw per-source files
(cat-merge style); `load` brings an existing graph in as-is.
"""

from __future__ import annotations

from pathlib import Path

from koza.model.graph_operations import JoinResult, LoadConfig

from .join import join_graphs, prepare_file_specs_from_paths


def load_graph(config: LoadConfig) -> JoinResult:
    """Load KGX node/edge files into a DuckDB as `nodes` / `edges` tables.

    A thin wrapper over `join_graphs` that uses `LoadConfig`'s faithful-load
    defaults. Returns the same `JoinResult` as `join_graphs`.
    """
    return join_graphs(config)


def prepare_load_config_from_paths(
    node_files: list[Path],
    edge_files: list[Path],
    output_database: Path | None = None,
    **kwargs,
) -> LoadConfig:
    """Build a `LoadConfig` from node/edge file paths, auto-generating FileSpecs.

    Mirrors `prepare_merge_config_from_paths`: formats and file types are
    auto-detected from the paths, and any extra `LoadConfig` options pass
    through via `kwargs` (e.g. `quiet`, `show_progress`, `slots_file`).
    """
    node_specs, edge_specs = prepare_file_specs_from_paths(
        [str(f) for f in node_files], [str(f) for f in edge_files]
    )
    return LoadConfig(
        node_files=node_specs,
        edge_files=edge_specs,
        output_database=output_database,
        **kwargs,
    )
