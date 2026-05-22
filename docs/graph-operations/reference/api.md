# Python API Reference

This reference documentation is auto-generated from the source code docstrings using [mkdocstrings](https://mkdocstrings.github.io/). Each function includes parameter descriptions, return types, and usage examples.

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

### closurize_graph

Apply transitive closure expansion to a merged graph. Produces `denormalized_nodes` and `denormalized_edges` as views joining `nodes`/`edges` to materialized closure side tables. Evolves the stored graph schema to include `DenormalizedEntity` and `DenormalizedAssociation` classes.

::: koza.graph_operations.closurize.closurize_graph
    options:
      show_root_heading: true
      show_source: false

## Graph Schema Seam

Each koza-built DuckDB carries its own derived LinkML schema in a `_koza_schema` metadata table, seeded at graph creation from Biolink + input file headers + koza extras. Operations consume and evolve this schema through the functions below.

### seed_schema

Derive a graph schema from input headers + Biolink and persist it into the DuckDB at graph creation.

::: koza.graph_operations.graph_schema.seed_schema
    options:
      show_root_heading: true
      show_source: false

### current_schema

Read the stored schema back from a DuckDB.

::: koza.graph_operations.graph_schema.current_schema
    options:
      show_root_heading: true
      show_source: false

### is_seeded

Check whether a DuckDB has a stored schema (e.g. before calling `update_schema`).

::: koza.graph_operations.graph_schema.is_seeded
    options:
      show_root_heading: true
      show_source: false

### ensure_slots

Materialize declared output slots as columns, idempotently. Used by operations (`normalize`, `closurize`) before they write columns they've declared.

::: koza.graph_operations.graph_schema.ensure_slots
    options:
      show_root_heading: true
      show_source: false

### update_schema

Persist an evolved schema back to the DuckDB.

::: koza.graph_operations.graph_schema.update_schema
    options:
      show_root_heading: true
      show_source: false

### export_schema

Project the stored schema to a release-ready YAML string (Denormalized\* classes renamed to Entity/Association, multivalued info derived from actual column types, linkml:types import + prefixes declared).

::: koza.graph_operations.graph_schema.export_schema
    options:
      show_root_heading: true
      show_source: false

### stored_biolink_yaml

Read the full Biolink YAML stored at seed time (used by `koza schema rebase`, not by routine operations).

::: koza.graph_operations.graph_schema.stored_biolink_yaml
    options:
      show_root_heading: true
      show_source: false

### discover_declared_outputs

Walk operation modules to collect their `DECLARED_OUTPUTS` for inclusion in the seeded schema's strict-reject set.

::: koza.graph_operations.graph_schema.discover_declared_outputs
    options:
      show_root_heading: true
      show_source: false

## Reporting Functions

These functions generate various reports and statistics about graph databases.

### generate_qc_report

Generate a quality control report.

::: koza.graph_operations.report.generate_qc_report
    options:
      show_root_heading: true
      show_source: false

### generate_graph_stats

Generate graph statistics.

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
