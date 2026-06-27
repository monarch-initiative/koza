"""
Graph Operations and Analysis Toolkit for Koza

This module provides DuckDB-centered graph operations for KGX data manipulation,
including join, split, normalize, dedupe, prune, and other graph analysis operations.
"""

from .append import append_graphs
from .closurize import closurize_graph
from .connectivity import generate_connectivity_report
from .deduplicate import deduplicate_graph
from .export import convert_graph, export_graph
from .join import join_graphs, prepare_file_specs_from_paths
from .load import load_graph, prepare_load_config_from_paths
from .merge import merge_graphs, prepare_merge_config_from_paths
from .normalize import normalize_graph, prepare_mapping_file_specs_from_paths
from .profile import detect_categorical_columns, profile_graph, render_profile
from .prune import prune_graph
from .report import (
    generate_edge_examples,
    generate_edge_report,
    generate_graph_stats,
    generate_node_examples,
    generate_node_report,
    generate_qc_report,
    generate_schema_compliance_report,
)
from .information_content import compute_information_content
from .schema import generate_schema_report, print_schema_summary, write_schema_report_yaml
from .split import split_graph
from .utils import GraphDatabase, print_operation_summary
from .biolink_check import run_biolink_check

__all__ = [
    "join_graphs",
    "load_graph",
    "prepare_load_config_from_paths",
    "profile_graph",
    "render_profile",
    "detect_categorical_columns",
    "split_graph",
    "export_graph",
    "convert_graph",
    "prune_graph",
    "append_graphs",
    "closurize_graph",
    "compute_information_content",
    "deduplicate_graph",
    "normalize_graph",
    "merge_graphs",
    "prepare_file_specs_from_paths",
    "prepare_mapping_file_specs_from_paths",
    "prepare_merge_config_from_paths",
    "GraphDatabase",
    "print_operation_summary",
    "generate_schema_report",
    "write_schema_report_yaml",
    "print_schema_summary",
    "generate_qc_report",
    "generate_graph_stats",
    "generate_schema_compliance_report",
    # Connectivity (requires ensmallen)
    "generate_connectivity_report",
    # Tabular reports
    "generate_node_report",
    "generate_edge_report",
    "run_biolink_check",
    "generate_node_examples",
    "generate_edge_examples",
]
