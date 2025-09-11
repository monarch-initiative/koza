#!/usr/bin/env python3
"""CLI for Koza - wraps the koza library to provide a command line interface"""

from collections import defaultdict
from pathlib import Path
from typing import Annotated, Optional, List
import glob

import typer
from loguru import logger
from tqdm import tqdm

from koza.model.formats import OutputFormat
from koza.model.graph_operations import (
    JoinConfig, SplitConfig, PruneConfig, AppendConfig, NormalizeConfig, MergeConfig, 
    FileSpec, KGXFormat, KGXFileType, QCReportConfig, GraphStatsConfig, SchemaReportConfig
)
from koza.runner import KozaRunner
from koza.graph_operations import (
    join_graphs, split_graph, prune_graph, append_graphs, normalize_graph, merge_graphs, 
    prepare_file_specs_from_paths, prepare_mapping_file_specs_from_paths, prepare_merge_config_from_paths,
    generate_qc_report, generate_graph_stats, generate_schema_compliance_report
)

typer_app = typer.Typer(
    no_args_is_help=True,
)


@typer_app.callback(invoke_without_command=True)
def callback(version: Optional[bool] = typer.Option(None, "--version", is_eager=True)):
    if version:
        from koza import __version__

        typer.echo(f"Koza version: {__version__}")
        raise typer.Exit()


def parse_input_files(args: list[str]):
    tagged_ret: defaultdict[str, list[str]] = defaultdict(list)
    untagged_ret: list[str] = []
    parse_as_single_arg: bool | None = None
    for arg in args:
        parts = arg.split(":", 1)
        is_single_arg = len(parts) == 1

        if parse_as_single_arg is None:
            parse_as_single_arg = is_single_arg
        elif is_single_arg != parse_as_single_arg:
            raise ValueError("Cannot mix tagged and untagged input files")

        if is_single_arg:
            untagged_ret.append(parts[0])
        else:
            tagged_ret[parts[0]].append(parts[1])
    return untagged_ret if untagged_ret else dict(tagged_ret)


@typer_app.command()
def transform(
    configuration_yaml: Annotated[
        str,
        typer.Argument(help="Configuration YAML file"),
    ],
    input_files: Annotated[
        Optional[list[str]],
        typer.Option("--input-file", "-i", help="Override input files"),
    ] = None,
    output_dir: Annotated[
        str,
        typer.Option("--output-dir", "-o", help="Path to output directory"),
    ] = "./output",
    output_format: Annotated[
        OutputFormat,
        typer.Option("--output-format", "-f", help="Output format"),
    ] = OutputFormat.tsv,
    row_limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of rows to process (if skipped, processes entire source file)"),
    ] = 0,
    show_progress: Annotated[
        bool,
        typer.Option("--progress", "-p", help="Display progress of transform"),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Disable log output"),
    ] = False,
) -> None:
    """Transform a source file"""
    logger.remove()

    output_path = Path(output_dir)

    if output_path.exists() and not output_path.is_dir():
        raise NotADirectoryError(f"{output_dir} is not a directory")
    elif not output_path.exists():
        output_path.mkdir(parents=True)

    if not quiet:
        prompt = "{time:YYYY-MM-DD HH:mm:ss.SSS} | <level>{level}</level> | <level>{message}</level>"

        def log(msg: str):
            tqdm.write(msg, end="")

        logger.add(log, format=prompt, colorize=True)

    parsed_input_files = parse_input_files(input_files) if input_files else None

    # FIXME: Verbosity, logging
    config, runner = KozaRunner.from_config_file(
        configuration_yaml,
        input_files=parsed_input_files,
        output_dir=output_dir,
        output_format=output_format,
        row_limit=row_limit,
        show_progress=show_progress,
    )

    logger.info(f"Running transform for {config.name} with output to `{output_dir}`")

    runner.run()

    logger.info(f"Finished transform for {config.name}")


def _expand_file_patterns(patterns: List[str]) -> List[str]:
    """Expand glob patterns and return list of files."""
    expanded_files = []
    for pattern in patterns:
        # Expand glob pattern
        matches = glob.glob(pattern)
        if matches:
            expanded_files.extend(matches)
        else:
            # If no glob matches, treat as literal filename
            expanded_files.append(pattern)
    return expanded_files


def _discover_files_in_directory(directory: Path) -> tuple[List[str], List[str]]:
    """Discover node and edge files in a directory."""
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")
    
    # Look for node files
    node_patterns = ["*_nodes.tsv", "*_nodes.jsonl", "*_nodes.parquet", "nodes.*"]
    node_files = []
    for pattern in node_patterns:
        node_files.extend(glob.glob(str(directory / pattern)))
    
    # Look for edge files  
    edge_patterns = ["*_edges.tsv", "*_edges.jsonl", "*_edges.parquet", "edges.*"]
    edge_files = []
    for pattern in edge_patterns:
        edge_files.extend(glob.glob(str(directory / pattern)))
    
    return node_files, edge_files


@typer_app.command()
def join(
    node_files: Annotated[
        Optional[List[str]],
        typer.Option("--nodes", "-n", help="Node files or glob patterns (can specify multiple)")
    ] = None,
    edge_files: Annotated[
        Optional[List[str]], 
        typer.Option("--edges", "-e", help="Edge files or glob patterns (can specify multiple)")
    ] = None,
    input_directory: Annotated[
        Optional[str],
        typer.Option("--input-dir", "-d", help="Directory to auto-discover KGX files")
    ] = None,
    output_database: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Path to output database file (default: in-memory)")
    ] = None,
    output_format: Annotated[
        KGXFormat,
        typer.Option("--format", "-f", help="Output format for any exported files")
    ] = KGXFormat.TSV,
    schema_reporting: Annotated[
        bool,
        typer.Option("--schema-report", help="Generate schema compliance report")
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress output")
    ] = False,
    show_progress: Annotated[
        bool,
        typer.Option("--progress", "-p", help="Show progress bars")
    ] = True
) -> None:
    """Join multiple KGX files into a unified DuckDB database
    
    Examples:
        # Auto-discover files in directory
        koza join --input-dir tmp/ -o graph.duckdb
        
        # Use glob patterns
        koza join -n "tmp/*_nodes.tsv" -e "tmp/*_edges.tsv" -o graph.duckdb
        
        # Mix directory discovery with additional files
        koza join --input-dir tmp/ -n extra_nodes.tsv -o graph.duckdb
        
        # Multiple individual files
        koza join -n file1.tsv -n file2.tsv -e edges.tsv -o graph.duckdb
    """
    
    try:
        # Collect all node and edge files
        all_node_files = []
        all_edge_files = []
        
        # Auto-discover from directory if specified
        if input_directory:
            dir_path = Path(input_directory)
            discovered_nodes, discovered_edges = _discover_files_in_directory(dir_path)
            all_node_files.extend(discovered_nodes)
            all_edge_files.extend(discovered_edges)
            
            if not quiet:
                print(f"📂 Auto-discovered from {input_directory}:")
                print(f"   - {len(discovered_nodes)} node files")
                print(f"   - {len(discovered_edges)} edge files")
        
        # Add files from explicit options (with glob expansion)
        if node_files:
            expanded_nodes = _expand_file_patterns(node_files)
            all_node_files.extend(expanded_nodes)
            
            if not quiet and len(expanded_nodes) > len(node_files):
                print(f"🔍 Expanded {len(node_files)} node patterns to {len(expanded_nodes)} files")
        
        if edge_files:
            expanded_edges = _expand_file_patterns(edge_files)
            all_edge_files.extend(expanded_edges)
            
            if not quiet and len(expanded_edges) > len(edge_files):
                print(f"🔍 Expanded {len(edge_files)} edge patterns to {len(expanded_edges)} files")
        
        # Remove duplicates while preserving order
        all_node_files = list(dict.fromkeys(all_node_files))
        all_edge_files = list(dict.fromkeys(all_edge_files))
        
        # Validate we have at least some files
        if not all_node_files and not all_edge_files:
            if input_directory:
                raise typer.BadParameter(f"No KGX files found in directory: {input_directory}")
            else:
                raise typer.BadParameter("Must specify --input-dir, --nodes, or --edges")
        
        # Prepare file specifications
        node_specs, edge_specs = prepare_file_specs_from_paths(
            all_node_files, all_edge_files
        )
        
        # Create configuration
        config = JoinConfig(
            node_files=node_specs,
            edge_files=edge_specs,
            database_path=Path(output_database) if output_database else None,
            output_format=output_format,
            schema_reporting=schema_reporting,
            quiet=quiet,
            show_progress=show_progress
        )
        
        # Execute join operation
        result = join_graphs(config)
        
        if not quiet:
            typer.echo("Join operation completed successfully!")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@typer_app.command()
def split(
    file: Annotated[
        str,
        typer.Argument(help="Path to the KGX file to split")
    ],
    fields: Annotated[
        str,
        typer.Argument(help="Comma-separated list of fields to split on")
    ],
    output_dir: Annotated[
        str,
        typer.Option("--output-dir", "-o", help="Output directory for split files")
    ] = "./output",
    output_format: Annotated[
        Optional[KGXFormat],
        typer.Option("--format", "-f", help="Output format (default: preserve input format)")
    ] = None,
    remove_prefixes: Annotated[
        bool,
        typer.Option("--remove-prefixes", help="Remove prefixes from values in filenames")
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress output")
    ] = False,
    show_progress: Annotated[
        bool,
        typer.Option("--progress", "-p", help="Show progress bars")
    ] = True
) -> None:
    """Split a KGX file by specified fields with format conversion support"""
    
    try:
        # Create file specification
        input_path = Path(file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {file}")
        
        file_spec = FileSpec(path=input_path)
        
        # Parse split fields
        split_fields = [field.strip() for field in fields.split(",")]
        
        # Create configuration
        config = SplitConfig(
            input_file=file_spec,
            split_fields=split_fields,
            output_directory=Path(output_dir),
            output_format=output_format,
            remove_prefixes=remove_prefixes,
            quiet=quiet,
            show_progress=show_progress
        )
        
        # Execute split operation
        result = split_graph(config)
        
        if not quiet:
            typer.echo("Split operation completed successfully!")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@typer_app.command()
def prune(
    database: Annotated[
        str,
        typer.Argument(help="Path to the DuckDB database file to prune")
    ],
    keep_singletons: Annotated[
        bool,
        typer.Option("--keep-singletons", help="Keep singleton nodes in main table")
    ] = False,  # Will be set to True if remove_singletons is False
    remove_singletons: Annotated[
        bool,
        typer.Option("--remove-singletons", help="Move singleton nodes to separate table")
    ] = False,
    min_component_size: Annotated[
        Optional[int],
        typer.Option("--min-component-size", help="Minimum connected component size (experimental)")
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress output")
    ] = False,
    show_progress: Annotated[
        bool,
        typer.Option("--progress", "-p", help="Show progress bars")
    ] = True
) -> None:
    """Prune graph by removing dangling edges and handling singleton nodes
    
    Examples:
        # Keep singleton nodes, move dangling edges
        koza prune graph.duckdb
        
        # Remove singleton nodes to separate table
        koza prune graph.duckdb --remove-singletons
        
        # Experimental: filter small components
        koza prune graph.duckdb --min-component-size 10
    """
    
    try:
        database_path = Path(database)
        if not database_path.exists():
            raise typer.BadParameter(f"Database file not found: {database}")
        
        # Set default behavior: keep singletons unless explicitly removing
        if not keep_singletons and not remove_singletons:
            keep_singletons = True
        
        # Create configuration
        config = PruneConfig(
            database_path=database_path,
            keep_singletons=keep_singletons,
            remove_singletons=remove_singletons,
            min_component_size=min_component_size,
            quiet=quiet,
            show_progress=show_progress
        )
        
        # Execute prune operation
        result = prune_graph(config)
        
        if not quiet:
            typer.echo("Prune operation completed successfully!")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@typer_app.command()
def append(
    database: Annotated[
        str,
        typer.Argument(help="Path to existing DuckDB database file")
    ],
    node_files: Annotated[
        Optional[List[str]],
        typer.Option("--nodes", "-n", help="Node files or glob patterns (can specify multiple)")
    ] = None,
    edge_files: Annotated[
        Optional[List[str]], 
        typer.Option("--edges", "-e", help="Edge files or glob patterns (can specify multiple)")
    ] = None,
    input_directory: Annotated[
        Optional[str],
        typer.Option("--input-dir", "-d", help="Directory to auto-discover KGX files")
    ] = None,
    deduplicate: Annotated[
        bool,
        typer.Option("--deduplicate", help="Remove duplicates during append")
    ] = False,
    schema_reporting: Annotated[
        bool,
        typer.Option("--schema-report", help="Generate schema compliance report")
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress output")
    ] = False,
    show_progress: Annotated[
        bool,
        typer.Option("--progress", "-p", help="Show progress bars")
    ] = True
) -> None:
    """Append new KGX files to an existing graph database
    
    Examples:
        # Append specific files to existing database
        koza append graph.duckdb -n new_nodes.tsv -e new_edges.tsv
        
        # Auto-discover files in directory and append
        koza append graph.duckdb --input-dir new_data/
        
        # Append with deduplication and schema reporting
        koza append graph.duckdb -n "*.tsv" --deduplicate --schema-report
    """
    
    try:
        database_path = Path(database)
        if not database_path.exists():
            raise typer.BadParameter(f"Database file not found: {database}")
        
        # Collect all node and edge files
        all_node_files = []
        all_edge_files = []
        
        # Auto-discover from directory if specified
        if input_directory:
            dir_path = Path(input_directory)
            discovered_nodes, discovered_edges = _discover_files_in_directory(dir_path)
            all_node_files.extend(discovered_nodes)
            all_edge_files.extend(discovered_edges)
            
            if not quiet:
                print(f"📂 Auto-discovered from {input_directory}:")
                print(f"   - {len(discovered_nodes)} node files")
                print(f"   - {len(discovered_edges)} edge files")
        
        # Add files from explicit options (with glob expansion)
        if node_files:
            expanded_nodes = _expand_file_patterns(node_files)
            all_node_files.extend(expanded_nodes)
            
            if not quiet and len(expanded_nodes) > len(node_files):
                print(f"🔍 Expanded {len(node_files)} node patterns to {len(expanded_nodes)} files")
        
        if edge_files:
            expanded_edges = _expand_file_patterns(edge_files)
            all_edge_files.extend(expanded_edges)
            
            if not quiet and len(expanded_edges) > len(edge_files):
                print(f"🔍 Expanded {len(edge_files)} edge patterns to {len(expanded_edges)} files")
        
        # Remove duplicates while preserving order
        all_node_files = list(dict.fromkeys(all_node_files))
        all_edge_files = list(dict.fromkeys(all_edge_files))
        
        # Validate we have at least some files
        if not all_node_files and not all_edge_files:
            if input_directory:
                raise typer.BadParameter(f"No KGX files found in directory: {input_directory}")
            else:
                raise typer.BadParameter("Must specify --input-dir, --nodes, or --edges")
        
        # Prepare file specifications
        node_specs, edge_specs = prepare_file_specs_from_paths(
            all_node_files, all_edge_files
        )
        
        # Create configuration
        config = AppendConfig(
            database_path=database_path,
            node_files=node_specs,
            edge_files=edge_specs,
            deduplicate=deduplicate,
            schema_reporting=schema_reporting,
            quiet=quiet,
            show_progress=show_progress
        )
        
        # Execute append operation
        result = append_graphs(config)
        
        if not quiet:
            typer.echo("Append operation completed successfully!")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@typer_app.command()
def normalize(
    database: Annotated[
        str,
        typer.Argument(help="Path to existing DuckDB database file")
    ],
    mapping_files: Annotated[
        Optional[List[str]],
        typer.Option("--mappings", "-m", help="SSSOM mapping files or glob patterns (can specify multiple)")
    ] = None,
    mappings_directory: Annotated[
        Optional[str],
        typer.Option("--mappings-dir", "-d", help="Directory containing SSSOM mapping files")
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress output")
    ] = False,
    show_progress: Annotated[
        bool,
        typer.Option("--progress", "-p", help="Show progress bars")
    ] = True
) -> None:
    """Apply SSSOM mappings to normalize edge subject/object references
    
    This operation loads SSSOM mapping files and applies them to rewrite edge
    subject and object identifiers to their canonical/equivalent forms. Node
    identifiers themselves are not changed - only edge references are normalized.
    
    Examples:
        # Apply specific mapping files
        koza normalize graph.duckdb -m gene_mappings.sssom.tsv -m mondo.sssom.tsv
        
        # Auto-discover SSSOM files in directory
        koza normalize graph.duckdb --mappings-dir ./sssom/
        
        # Apply mappings with glob pattern
        koza normalize graph.duckdb -m "*.sssom.tsv"
    """
    
    try:
        database_path = Path(database)
        if not database_path.exists():
            raise typer.BadParameter(f"Database file not found: {database}")
        
        # Collect all mapping files
        all_mapping_files = []
        
        # Auto-discover from directory if specified
        if mappings_directory:
            dir_path = Path(mappings_directory)
            if not dir_path.exists():
                raise typer.BadParameter(f"Mappings directory not found: {mappings_directory}")
            
            # Look for SSSOM files (*.sssom.tsv)
            discovered_mappings = list(dir_path.glob("*.sssom.tsv"))
            all_mapping_files.extend([str(f) for f in discovered_mappings])
            
            if not quiet:
                print(f"📂 Auto-discovered {len(discovered_mappings)} SSSOM files from {mappings_directory}")
        
        # Add files from explicit options (with glob expansion)
        if mapping_files:
            expanded_mappings = _expand_file_patterns(mapping_files)
            all_mapping_files.extend(expanded_mappings)
            
            if not quiet and len(expanded_mappings) > len(mapping_files):
                print(f"🔍 Expanded {len(mapping_files)} mapping patterns to {len(expanded_mappings)} files")
        
        # Remove duplicates while preserving order
        all_mapping_files = list(dict.fromkeys(all_mapping_files))
        
        # Validate we have at least some mapping files
        if not all_mapping_files:
            if mappings_directory:
                raise typer.BadParameter(f"No SSSOM files found in directory: {mappings_directory}")
            else:
                raise typer.BadParameter("Must specify --mappings-dir or --mappings")
        
        # Prepare mapping file specifications
        mapping_specs = prepare_mapping_file_specs_from_paths(
            [Path(f) for f in all_mapping_files]
        )
        
        # Create configuration
        config = NormalizeConfig(
            database_path=database_path,
            mapping_files=mapping_specs,
            quiet=quiet,
            show_progress=show_progress
        )
        
        # Execute normalize operation
        result = normalize_graph(config)
        
        if not quiet:
            typer.echo("Normalize operation completed successfully!")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@typer_app.command()
def merge(
    node_files: Annotated[
        Optional[List[str]],
        typer.Option("--nodes", "-n", help="Node files or glob patterns (can specify multiple)")
    ] = None,
    edge_files: Annotated[
        Optional[List[str]], 
        typer.Option("--edges", "-e", help="Edge files or glob patterns (can specify multiple)")
    ] = None,
    mapping_files: Annotated[
        Optional[List[str]],
        typer.Option("--mappings", "-m", help="SSSOM mapping files or glob patterns (can specify multiple)")
    ] = None,
    input_directory: Annotated[
        Optional[str],
        typer.Option("--input-dir", "-d", help="Directory to auto-discover KGX files")
    ] = None,
    mappings_directory: Annotated[
        Optional[str],
        typer.Option("--mappings-dir", help="Directory containing SSSOM mapping files")
    ] = None,
    output_database: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Path to output database file (default: temporary)")
    ] = None,
    export_final: Annotated[
        bool,
        typer.Option("--export", help="Export final clean data to files")
    ] = False,
    export_directory: Annotated[
        Optional[str],
        typer.Option("--export-dir", help="Directory for exported files (required if --export)")
    ] = None,
    output_format: Annotated[
        KGXFormat,
        typer.Option("--format", "-f", help="Output format for exported files")
    ] = KGXFormat.TSV,
    archive: Annotated[
        bool,
        typer.Option("--archive", help="Export as archive (tar) instead of loose files")
    ] = False,
    compress: Annotated[
        bool,
        typer.Option("--compress", help="Compress archive as tar.gz (requires --archive)")
    ] = False,
    graph_name: Annotated[
        Optional[str],
        typer.Option("--graph-name", help="Name for graph files in archive (default: merged_graph)")
    ] = None,
    skip_normalize: Annotated[
        bool,
        typer.Option("--skip-normalize", help="Skip normalization step")
    ] = False,
    skip_prune: Annotated[
        bool,
        typer.Option("--skip-prune", help="Skip pruning step")
    ] = False,
    keep_singletons: Annotated[
        bool,
        typer.Option("--keep-singletons", help="Keep singleton nodes (default)")
    ] = True,
    remove_singletons: Annotated[
        bool,
        typer.Option("--remove-singletons", help="Move singleton nodes to separate table")
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress output")
    ] = False,
    show_progress: Annotated[
        bool,
        typer.Option("--progress", "-p", help="Show progress bars")
    ] = True
) -> None:
    """Complete merge pipeline: join → normalize → prune
    
    This composite operation orchestrates the full graph processing pipeline:
    1. Join: Load and combine multiple KGX files into a unified database
    2. Normalize: Apply SSSOM mappings to edge subject/object references  
    3. Prune: Remove dangling edges and handle singleton nodes
    
    The pipeline can be customized by skipping steps or configuring options.
    
    Examples:
        # Full pipeline with auto-discovery
        koza merge --input-dir ./data/ --mappings-dir ./sssom/ -o clean_graph.duckdb
        
        # Specific files with export
        koza merge -n nodes.tsv -e edges.tsv -m mappings.sssom.tsv --export --export-dir ./output/
        
        # Skip normalization, only join and prune
        koza merge -n "*.tsv" -e "*.tsv" --skip-normalize -o graph.duckdb
        
        # Custom singleton handling
        koza merge --input-dir ./data/ -m "*.sssom.tsv" --remove-singletons
    """
    
    try:
        # Collect all input files
        all_node_files = []
        all_edge_files = []
        all_mapping_files = []
        
        # Auto-discover from directory if specified
        if input_directory:
            dir_path = Path(input_directory)
            if not dir_path.exists():
                raise typer.BadParameter(f"Input directory not found: {input_directory}")
            
            discovered_nodes, discovered_edges = _discover_files_in_directory(dir_path)
            all_node_files.extend(discovered_nodes)
            all_edge_files.extend(discovered_edges)
            
            if not quiet:
                print(f"📂 Auto-discovered from {input_directory}:")
                print(f"   - {len(discovered_nodes)} node files")
                print(f"   - {len(discovered_edges)} edge files")
        
        # Add files from explicit options (with glob expansion)
        if node_files:
            expanded_nodes = _expand_file_patterns(node_files)
            all_node_files.extend(expanded_nodes)
            
            if not quiet and len(expanded_nodes) > len(node_files):
                print(f"🔍 Expanded {len(node_files)} node patterns to {len(expanded_nodes)} files")
        
        if edge_files:
            expanded_edges = _expand_file_patterns(edge_files)
            all_edge_files.extend(expanded_edges)
            
            if not quiet and len(expanded_edges) > len(edge_files):
                print(f"🔍 Expanded {len(edge_files)} edge patterns to {len(expanded_edges)} files")
        
        # Auto-discover mappings from directory if specified
        if mappings_directory:
            dir_path = Path(mappings_directory)
            if not dir_path.exists():
                raise typer.BadParameter(f"Mappings directory not found: {mappings_directory}")
            
            discovered_mappings = list(dir_path.glob("*.sssom.tsv"))
            all_mapping_files.extend([str(f) for f in discovered_mappings])
            
            if not quiet:
                print(f"📂 Auto-discovered {len(discovered_mappings)} SSSOM files from {mappings_directory}")
        
        # Add mapping files from explicit options
        if mapping_files:
            expanded_mappings = _expand_file_patterns(mapping_files)
            all_mapping_files.extend(expanded_mappings)
            
            if not quiet and len(expanded_mappings) > len(mapping_files):
                print(f"🔍 Expanded {len(mapping_files)} mapping patterns to {len(expanded_mappings)} files")
        
        # Remove duplicates while preserving order
        all_node_files = list(dict.fromkeys(all_node_files))
        all_edge_files = list(dict.fromkeys(all_edge_files))
        all_mapping_files = list(dict.fromkeys(all_mapping_files))
        
        # Validate inputs
        if not all_node_files and not all_edge_files:
            if input_directory:
                raise typer.BadParameter(f"No KGX files found in directory: {input_directory}")
            else:
                raise typer.BadParameter("Must specify --input-dir, --nodes, or --edges")
        
        if not skip_normalize and not all_mapping_files:
            if mappings_directory:
                raise typer.BadParameter(f"No SSSOM files found in directory: {mappings_directory}")
            else:
                raise typer.BadParameter("Must specify --mappings-dir, --mappings, or --skip-normalize")
        
        if export_final and not export_directory:
            raise typer.BadParameter("Must specify --export-dir when using --export")
        
        if compress and not archive:
            raise typer.BadParameter("--compress requires --archive to be enabled")
        
        # Prepare file specifications
        config = prepare_merge_config_from_paths(
            node_files=[Path(f) for f in all_node_files],
            edge_files=[Path(f) for f in all_edge_files],
            mapping_files=[Path(f) for f in all_mapping_files],
            output_database=Path(output_database) if output_database else None,
            skip_normalize=skip_normalize,
            skip_prune=skip_prune,
            keep_singletons=keep_singletons,
            remove_singletons=remove_singletons,
            export_final=export_final,
            export_directory=Path(export_directory) if export_directory else None,
            output_format=output_format,
            archive=archive,
            compress=compress,
            graph_name=graph_name,
            quiet=quiet,
            show_progress=show_progress
        )
        
        # Execute merge pipeline
        result = merge_graphs(config)
        
        if not quiet:
            if result.success:
                typer.echo("Merge pipeline completed successfully!")
                if result.exported_files:
                    print(f"📁 Exported files: {len(result.exported_files)}")
                    for file_path in result.exported_files:
                        print(f"   - {file_path}")
            else:
                typer.echo("Merge pipeline completed with errors!")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


# Report Commands

@typer_app.command(name="report")
def report_cmd(
    report_type: Annotated[
        str,
        typer.Argument(help="Type of report to generate: qc, graph-stats, or schema")
    ],
    database: Annotated[
        str,
        typer.Option("--database", "-d", help="Path to DuckDB database file")
    ],
    output: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Path to output report file (YAML format)")
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress progress output")
    ] = False,
):
    """
    Generate comprehensive reports for KGX graph databases.
    
    Available report types:
    
    • qc: Quality control analysis by data source
    
    • graph-stats: Comprehensive graph statistics (similar to merged_graph_stats.yaml)
    
    • schema: Database schema analysis and biolink compliance
    
    Examples:
    
        # Generate QC report
        koza report qc -d merged.duckdb -o qc_report.yaml
        
        # Generate graph statistics
        koza report graph-stats -d merged.duckdb -o graph_stats.yaml
        
        # Generate schema report  
        koza report schema -d merged.duckdb -o schema_report.yaml
        
        # Quick QC analysis (console output only)
        koza report qc -d merged.duckdb
    """
    
    try:
        database_path = Path(database)
        if not database_path.exists():
            raise typer.BadParameter(f"Database file not found: {database}")
        
        output_path = Path(output) if output else None
        
        if report_type == "qc":
            config = QCReportConfig(
                database_path=database_path,
                output_file=output_path,
                quiet=quiet
            )
            result = generate_qc_report(config)
            
            if not quiet:
                typer.echo("✓ QC report generated successfully")
                if result.output_file:
                    typer.echo(f"Report saved to: {result.output_file}")
                    
        elif report_type == "graph-stats":
            config = GraphStatsConfig(
                database_path=database_path,
                output_file=output_path,
                quiet=quiet
            )
            result = generate_graph_stats(config)
            
            if not quiet:
                typer.echo("✓ Graph statistics report generated successfully")
                if result.output_file:
                    typer.echo(f"Report saved to: {result.output_file}")
                    
        elif report_type == "schema":
            config = SchemaReportConfig(
                database_path=database_path,
                output_file=output_path,
                quiet=quiet
            )
            result = generate_schema_compliance_report(config)
            
            if not quiet:
                typer.echo("✓ Schema report generated successfully")
                if result.output_file:
                    typer.echo(f"Report saved to: {result.output_file}")
                    
        else:
            raise typer.BadParameter(f"Unknown report type: {report_type}. Choose from: qc, graph-stats, schema")
            
    except Exception as e:
        typer.echo(f"Error generating {report_type} report: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    typer_app()
