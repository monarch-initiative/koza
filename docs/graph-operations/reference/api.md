# Python API Reference

This reference documentation is auto-generated from the source code docstrings using [mkdocstrings](https://mkdocstrings.github.io/). Each function includes detailed parameter descriptions, return types, and usage examples.

## Core Operations

These are the primary graph transformation functions. Each operation takes a configuration object and returns a result object with statistics and output information.

### join_graphs

Combine multiple KGX files into a single DuckDB database.

::: koza.graph_operations.join.join_graphs
    options:
      show_root_heading: true
      show_source: false

### split_graph

Split a graph database into separate files based on column values.

::: koza.graph_operations.split.split_graph
    options:
      show_root_heading: true
      show_source: false

### merge_graphs

End-to-end pipeline combining join, normalize, deduplicate, and prune operations.

::: koza.graph_operations.merge.merge_graphs
    options:
      show_root_heading: true
      show_source: false

### normalize_graph

Apply SSSOM mappings to normalize identifiers in a graph.

::: koza.graph_operations.normalize.normalize_graph
    options:
      show_root_heading: true
      show_source: false

### deduplicate_graph

Remove duplicate nodes and edges from a graph database.

::: koza.graph_operations.deduplicate.deduplicate_graph
    options:
      show_root_heading: true
      show_source: false

### prune_graph

Remove dangling edges and optionally singleton nodes from a graph.

::: koza.graph_operations.prune.prune_graph
    options:
      show_root_heading: true
      show_source: false

### append_graphs

Append additional KGX files to an existing graph database.

::: koza.graph_operations.append.append_graphs
    options:
      show_root_heading: true
      show_source: false

## Reporting Functions

These functions generate various reports and statistics about graph databases.

### generate_qc_report

Generate a comprehensive quality control report.

::: koza.graph_operations.report.generate_qc_report
    options:
      show_root_heading: true
      show_source: false

### generate_graph_stats

Generate detailed graph statistics.

::: koza.graph_operations.report.generate_graph_stats
    options:
      show_root_heading: true
      show_source: false

### generate_schema_compliance_report

Generate a schema analysis and biolink compliance report.

::: koza.graph_operations.report.generate_schema_compliance_report
    options:
      show_root_heading: true
      show_source: false

### generate_node_report

Generate a tabular node report grouped by categorical columns.

::: koza.graph_operations.report.generate_node_report
    options:
      show_root_heading: true
      show_source: false

### generate_edge_report

Generate a tabular edge report with denormalized node information.

::: koza.graph_operations.report.generate_edge_report
    options:
      show_root_heading: true
      show_source: false

### generate_node_examples

Generate sample nodes for each node type in the graph.

::: koza.graph_operations.report.generate_node_examples
    options:
      show_root_heading: true
      show_source: false

### generate_edge_examples

Generate sample edges for each edge type pattern in the graph.

::: koza.graph_operations.report.generate_edge_examples
    options:
      show_root_heading: true
      show_source: false

## Helper Functions

These utility functions simplify common tasks like converting file paths to FileSpec objects.

### prepare_file_specs_from_paths

Convert file paths to FileSpec objects with format auto-detection.

::: koza.graph_operations.join.prepare_file_specs_from_paths
    options:
      show_root_heading: true
      show_source: false

### prepare_merge_config_from_paths

Create a MergeConfig from file paths with automatic FileSpec generation.

::: koza.graph_operations.merge.prepare_merge_config_from_paths
    options:
      show_root_heading: true
      show_source: false

### prepare_mapping_file_specs_from_paths

Convert SSSOM mapping file paths to FileSpec objects.

::: koza.graph_operations.normalize.prepare_mapping_file_specs_from_paths
    options:
      show_root_heading: true
      show_source: false
