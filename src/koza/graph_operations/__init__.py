"""
Graph Operations and Analysis Toolkit for Koza

This module provides DuckDB-centered graph operations for KGX data manipulation,
including join, split, normalize, dedupe, prune, and other graph analysis operations.
"""

from .join import join_graphs, prepare_file_specs_from_paths
from .split import split_graph
from .prune import prune_graph
from .append import append_graphs
from .normalize import normalize_graph, prepare_mapping_file_specs_from_paths
from .merge import merge_graphs, prepare_merge_config_from_paths
from .utils import GraphDatabase, print_operation_summary
from .schema import generate_schema_report, write_schema_report_yaml, print_schema_summary

__all__ = [
    "join_graphs", 
    "split_graph", 
    "prune_graph",
    "append_graphs",
    "normalize_graph",
    "merge_graphs",
    "prepare_file_specs_from_paths",
    "prepare_mapping_file_specs_from_paths",
    "prepare_merge_config_from_paths",
    "GraphDatabase",
    "print_operation_summary",
    "generate_schema_report",
    "write_schema_report_yaml", 
    "print_schema_summary"
]