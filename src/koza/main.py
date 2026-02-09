#!/usr/bin/env python3
"""CLI for Koza - wraps the koza library to provide a command line interface"""

import glob
from collections import defaultdict
from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from tqdm import tqdm

from koza.graph_operations import (
    append_graphs,
    generate_edge_examples,
    generate_edge_report,
    generate_graph_stats,
    generate_node_examples,
    generate_node_report,
    generate_qc_report,
    generate_schema_compliance_report,
    join_graphs,
    merge_graphs,
    normalize_graph,
    prepare_file_specs_from_paths,
    prepare_mapping_file_specs_from_paths,
    prepare_merge_config_from_paths,
    prune_graph,
    split_graph,
    validate_graph,
)
from koza.model.formats import InputFormat, OutputFormat
from koza.model.graph_operations import (
    AppendConfig,
    EdgeExamplesConfig,
    EdgeReportConfig,
    FileSpec,
    GraphStatsConfig,
    JoinConfig,
    KGXFormat,
    NodeExamplesConfig,
    NodeReportConfig,
    NormalizeConfig,
    PruneConfig,
    QCReportConfig,
    SchemaReportConfig,
    SplitConfig,
    TabularReportFormat,
    ValidationConfig,
)
from koza.model.koza import KozaConfig
from koza.model.reader import CSVReaderConfig, JSONLReaderConfig, JSONReaderConfig, YAMLReaderConfig
from koza.model.transform import TransformConfig
from koza.model.writer import WriterConfig
from koza.runner import KozaRunner

typer_app = typer.Typer(
    no_args_is_help=True,
)


@typer_app.callback(invoke_without_command=True)
def callback(version: bool | None = typer.Option(None, "--version", is_eager=True)):
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


def _infer_input_format(files: list[str]) -> InputFormat:
    """Infer input format from file extensions.

    Args:
        files: List of file paths

    Returns:
        Inferred InputFormat

    Raises:
        ValueError: If no files provided or extension not recognized
    """
    ext_to_format = {
        ".yaml": InputFormat.yaml,
        ".yml": InputFormat.yaml,
        ".json": InputFormat.json,
        ".jsonl": InputFormat.jsonl,
        ".tsv": InputFormat.csv,
        ".csv": InputFormat.csv,
    }

    if not files:
        raise ValueError("No files provided. Cannot infer input format from empty file list.")

    ext = Path(files[0]).suffix.lower()
    if ext not in ext_to_format:
        raise ValueError(f"Cannot infer format from extension '{ext}'. Use --input-format.")

    return ext_to_format[ext]


@typer_app.command()
def transform(
    config_or_transform: Annotated[
        str,
        typer.Argument(help="Configuration YAML file OR Python transform file"),
    ],
    input_format: Annotated[
        InputFormat | None,
        typer.Option("--input-format", help="Input format (auto-detected if not specified)"),
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
    delimiter: Annotated[
        str | None,
        typer.Option("--delimiter", "-d", help="Field delimiter for CSV/TSV files (default: tab for .tsv, comma for .csv)"),
    ] = None,
    input_files: Annotated[
        list[str] | None,
        typer.Argument(help="Input files (required for .py transforms, supports shell glob expansion)"),
    ] = None,
) -> None:
    """Transform a source file.

    Accepts either a config YAML file or a Python transform file directly.

    Examples:
        # With config file (existing behavior)
        koza transform config.yaml

        # Config-free mode with transform file (shell expands the glob)
        koza transform transform.py -o ./output -f jsonl data/*.yaml

        # With output options
        koza transform transform.py -f jsonl -o ./output data/*.yaml

        # Explicit input format
        koza transform transform.py --input-format yaml data/*.dat

        # CSV with comma delimiter (default for .csv files)
        koza transform transform.py data/*.csv

        # TSV with explicit delimiter
        koza transform transform.py -d '\\t' data/*.txt
    """
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

    input_path = Path(config_or_transform)
    is_transform_file = input_path.suffix == ".py"

    if is_transform_file:
        # Config-free mode: build config from CLI args
        if not input_files:
            raise typer.BadParameter("Input files required when using a .py transform file. Provide files as positional arguments after the transform file.")

        detected_format = input_format or _infer_input_format(input_files)

        # Create appropriate reader config based on format
        if detected_format == InputFormat.csv:
            # Infer delimiter from file extension if not provided
            if delimiter is None:
                ext = Path(input_files[0]).suffix.lower()
                inferred_delimiter = "," if ext == ".csv" else "\t"
            else:
                inferred_delimiter = delimiter
            reader_config = CSVReaderConfig(files=input_files, delimiter=inferred_delimiter)
        else:
            reader_configs = {
                InputFormat.yaml: YAMLReaderConfig,
                InputFormat.json: JSONReaderConfig,
                InputFormat.jsonl: JSONLReaderConfig,
            }
            reader_config = reader_configs[detected_format](files=input_files)

        # Default node and edge properties for KGX output
        default_node_properties = ["id", "category", "name", "description", "xref", "provided_by", "synonym"]
        default_edge_properties = ["id", "subject", "predicate", "object", "category", "provided_by"]

        config = KozaConfig(
            name=input_path.stem,
            reader=reader_config,
            transform=TransformConfig(code=str(input_path)),
            writer=WriterConfig(
                format=output_format,
                node_properties=default_node_properties,
                edge_properties=default_edge_properties,
            ),
        )

        runner = KozaRunner.from_config(
            config,
            base_directory=Path.cwd(),
            output_dir=output_dir,
            row_limit=row_limit,
            show_progress=show_progress,
        )
    else:
        # Existing behavior: load from config file
        parsed_input_files = parse_input_files(input_files) if input_files else None

        config, runner = KozaRunner.from_config_file(
            config_or_transform,
            input_files=parsed_input_files,
            output_dir=output_dir,
            output_format=output_format,
            row_limit=row_limit,
            show_progress=show_progress,
        )

    logger.info(f"Running transform for {config.name} with output to `{output_dir}`")

    runner.run()

    logger.info(f"Finished transform for {config.name}")


def _expand_file_patterns(patterns: list[str]) -> list[str]:
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


def _discover_files_in_directory(directory: Path) -> tuple[list[str], list[str]]:
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
        list[str] | None, typer.Option("--nodes", "-n", help="Node files or glob patterns (can specify multiple)")
    ] = None,
    edge_files: Annotated[
        list[str] | None, typer.Option("--edges", "-e", help="Edge files or glob patterns (can specify multiple)")
    ] = None,
    input_directory: Annotated[
        str | None, typer.Option("--input-dir", "-d", help="Directory to auto-discover KGX files")
    ] = None,
    output_database: Annotated[
        str | None, typer.Option("--output", "-o", help="Path to output database file (default: in-memory)")
    ] = None,
    output_format: Annotated[
        KGXFormat, typer.Option("--format", "-f", help="Output format for any exported files")
    ] = KGXFormat.TSV,
    schema_reporting: Annotated[
        bool, typer.Option("--schema-report", help="Generate schema compliance report")
    ] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress output")] = False,
    show_progress: Annotated[bool, typer.Option("--progress", "-p", help="Show progress bars")] = True,
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
        node_specs, edge_specs = prepare_file_specs_from_paths(all_node_files, all_edge_files)

        # Create configuration
        config = JoinConfig(
            node_files=node_specs,
            edge_files=edge_specs,
            database_path=Path(output_database) if output_database else None,
            output_format=output_format,
            schema_reporting=schema_reporting,
            quiet=quiet,
            show_progress=show_progress,
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
    file: Annotated[str, typer.Argument(help="Path to the KGX file to split")],
    fields: Annotated[str, typer.Argument(help="Comma-separated list of fields to split on")],
    output_dir: Annotated[
        str, typer.Option("--output-dir", "-o", help="Output directory for split files")
    ] = "./output",
    output_format: Annotated[
        KGXFormat | None, typer.Option("--format", "-f", help="Output format (default: preserve input format)")
    ] = None,
    remove_prefixes: Annotated[
        bool, typer.Option("--remove-prefixes", help="Remove prefixes from values in filenames")
    ] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress output")] = False,
    show_progress: Annotated[bool, typer.Option("--progress", "-p", help="Show progress bars")] = True,
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
            show_progress=show_progress,
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
    database: Annotated[str, typer.Argument(help="Path to the DuckDB database file to prune")],
    keep_singletons: Annotated[
        bool, typer.Option("--keep-singletons", help="Keep singleton nodes in main table")
    ] = False,  # Will be set to True if remove_singletons is False
    remove_singletons: Annotated[
        bool, typer.Option("--remove-singletons", help="Move singleton nodes to separate table")
    ] = False,
    min_component_size: Annotated[
        int | None, typer.Option("--min-component-size", help="Minimum connected component size (experimental)")
    ] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress output")] = False,
    show_progress: Annotated[bool, typer.Option("--progress", "-p", help="Show progress bars")] = True,
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
            show_progress=show_progress,
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
    database: Annotated[str, typer.Argument(help="Path to existing DuckDB database file")],
    node_files: Annotated[
        list[str] | None, typer.Option("--nodes", "-n", help="Node files or glob patterns (can specify multiple)")
    ] = None,
    edge_files: Annotated[
        list[str] | None, typer.Option("--edges", "-e", help="Edge files or glob patterns (can specify multiple)")
    ] = None,
    input_directory: Annotated[
        str | None, typer.Option("--input-dir", "-d", help="Directory to auto-discover KGX files")
    ] = None,
    deduplicate: Annotated[bool, typer.Option("--deduplicate", help="Remove duplicates during append")] = False,
    schema_reporting: Annotated[
        bool, typer.Option("--schema-report", help="Generate schema compliance report")
    ] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress output")] = False,
    show_progress: Annotated[bool, typer.Option("--progress", "-p", help="Show progress bars")] = True,
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
        node_specs, edge_specs = prepare_file_specs_from_paths(all_node_files, all_edge_files)

        # Create configuration
        config = AppendConfig(
            database_path=database_path,
            node_files=node_specs,
            edge_files=edge_specs,
            deduplicate=deduplicate,
            schema_reporting=schema_reporting,
            quiet=quiet,
            show_progress=show_progress,
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
    database: Annotated[str, typer.Argument(help="Path to existing DuckDB database file")],
    mapping_files: Annotated[
        list[str] | None,
        typer.Option("--mappings", "-m", help="SSSOM mapping files or glob patterns (can specify multiple)"),
    ] = None,
    mappings_directory: Annotated[
        str | None, typer.Option("--mappings-dir", "-d", help="Directory containing SSSOM mapping files")
    ] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress output")] = False,
    show_progress: Annotated[bool, typer.Option("--progress", "-p", help="Show progress bars")] = True,
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
        mapping_specs = prepare_mapping_file_specs_from_paths([Path(f) for f in all_mapping_files])

        # Create configuration
        config = NormalizeConfig(
            database_path=database_path, mapping_files=mapping_specs, quiet=quiet, show_progress=show_progress
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
        list[str] | None, typer.Option("--nodes", "-n", help="Node files or glob patterns (can specify multiple)")
    ] = None,
    edge_files: Annotated[
        list[str] | None, typer.Option("--edges", "-e", help="Edge files or glob patterns (can specify multiple)")
    ] = None,
    mapping_files: Annotated[
        list[str] | None,
        typer.Option("--mappings", "-m", help="SSSOM mapping files or glob patterns (can specify multiple)"),
    ] = None,
    input_directory: Annotated[
        str | None, typer.Option("--input-dir", "-d", help="Directory to auto-discover KGX files")
    ] = None,
    mappings_directory: Annotated[
        str | None, typer.Option("--mappings-dir", help="Directory containing SSSOM mapping files")
    ] = None,
    output_database: Annotated[
        str | None, typer.Option("--output", "-o", help="Path to output database file (default: temporary)")
    ] = None,
    export_final: Annotated[bool, typer.Option("--export", help="Export final clean data to files")] = False,
    export_directory: Annotated[
        str | None, typer.Option("--export-dir", help="Directory for exported files (required if --export)")
    ] = None,
    output_format: Annotated[
        KGXFormat, typer.Option("--format", "-f", help="Output format for exported files")
    ] = KGXFormat.TSV,
    archive: Annotated[bool, typer.Option("--archive", help="Export as archive (tar) instead of loose files")] = False,
    compress: Annotated[
        bool, typer.Option("--compress", help="Compress archive as tar.gz (requires --archive)")
    ] = False,
    graph_name: Annotated[
        str | None, typer.Option("--graph-name", help="Name for graph files in archive (default: merged_graph)")
    ] = None,
    skip_normalize: Annotated[bool, typer.Option("--skip-normalize", help="Skip normalization step")] = False,
    skip_prune: Annotated[bool, typer.Option("--skip-prune", help="Skip pruning step")] = False,
    keep_singletons: Annotated[bool, typer.Option("--keep-singletons", help="Keep singleton nodes (default)")] = True,
    remove_singletons: Annotated[
        bool, typer.Option("--remove-singletons", help="Move singleton nodes to separate table")
    ] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress output")] = False,
    show_progress: Annotated[bool, typer.Option("--progress", "-p", help="Show progress bars")] = True,
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
            show_progress=show_progress,
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
    report_type: Annotated[str, typer.Argument(help="Type of report to generate: qc, graph-stats, or schema")],
    database: Annotated[str, typer.Option("--database", "-d", help="Path to DuckDB database file")],
    output: Annotated[
        str | None, typer.Option("--output", "-o", help="Path to output report file (YAML format)")
    ] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress progress output")] = False,
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
            config = QCReportConfig(database_path=database_path, output_file=output_path, quiet=quiet)
            result = generate_qc_report(config)

            if not quiet:
                typer.echo("✓ QC report generated successfully")
                if result.output_file:
                    typer.echo(f"Report saved to: {result.output_file}")

        elif report_type == "graph-stats":
            config = GraphStatsConfig(database_path=database_path, output_file=output_path, quiet=quiet)
            result = generate_graph_stats(config)

            if not quiet:
                typer.echo("✓ Graph statistics report generated successfully")
                if result.output_file:
                    typer.echo(f"Report saved to: {result.output_file}")

        elif report_type == "schema":
            config = SchemaReportConfig(database_path=database_path, output_file=output_path, quiet=quiet)
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


# Tabular Report Commands


@typer_app.command(name="node-report")
def node_report_cmd(
    database: Annotated[
        str | None, typer.Option("--database", "-d", help="Path to DuckDB database file")
    ] = None,
    node_file: Annotated[
        str | None, typer.Option("--file", "-f", help="Path to node file (TSV, JSONL, or Parquet)")
    ] = None,
    output: Annotated[str, typer.Option("--output", "-o", help="Path to output report file")] = None,
    format: Annotated[
        TabularReportFormat, typer.Option("--format", help="Output format")
    ] = TabularReportFormat.TSV,
    columns: Annotated[
        list[str] | None,
        typer.Option("--column", "-c", help="Categorical columns to group by (can specify multiple)"),
    ] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress progress output")] = False,
):
    """
    Generate tabular node report with GROUP BY ALL categorical columns.

    Outputs count of nodes grouped by categorical columns (namespace, category, etc.).

    Examples:

        # From database
        koza node-report -d merged.duckdb -o node_report.tsv

        # From file
        koza node-report -f nodes.tsv -o node_report.parquet --format parquet

        # Custom columns
        koza node-report -d merged.duckdb -o report.tsv -c namespace -c category -c provided_by
    """
    try:
        if not database and not node_file:
            raise typer.BadParameter("Must specify either --database or --file")

        # Build config
        config_kwargs = {
            "output_file": Path(output) if output else None,
            "output_format": format,
            "quiet": quiet,
        }

        if database:
            db_path = Path(database)
            if not db_path.exists():
                raise typer.BadParameter(f"Database file not found: {database}")
            config_kwargs["database_path"] = db_path
        else:
            file_path = Path(node_file)
            if not file_path.exists():
                raise typer.BadParameter(f"Node file not found: {node_file}")
            config_kwargs["node_file"] = FileSpec(path=file_path)

        if columns:
            config_kwargs["categorical_columns"] = columns

        config = NodeReportConfig(**config_kwargs)
        result = generate_node_report(config)

        if not quiet:
            typer.echo("✓ Node report generated successfully")
            if result.output_file:
                typer.echo(f"Report saved to: {result.output_file}")

    except Exception as e:
        typer.echo(f"Error generating node report: {e}", err=True)
        raise typer.Exit(1)


@typer_app.command(name="edge-report")
def edge_report_cmd(
    database: Annotated[
        str | None, typer.Option("--database", "-d", help="Path to DuckDB database file")
    ] = None,
    node_file: Annotated[
        str | None, typer.Option("--nodes", "-n", help="Path to node file (for denormalization)")
    ] = None,
    edge_file: Annotated[
        str | None, typer.Option("--edges", "-e", help="Path to edge file (TSV, JSONL, or Parquet)")
    ] = None,
    output: Annotated[str, typer.Option("--output", "-o", help="Path to output report file")] = None,
    format: Annotated[
        TabularReportFormat, typer.Option("--format", help="Output format")
    ] = TabularReportFormat.TSV,
    columns: Annotated[
        list[str] | None,
        typer.Option("--column", "-c", help="Categorical columns to group by (can specify multiple)"),
    ] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress progress output")] = False,
):
    """
    Generate tabular edge report with denormalized node info.

    Joins edges to nodes to get subject_category, object_category, etc., then
    outputs count of edges grouped by categorical columns.

    Examples:

        # From database
        koza edge-report -d merged.duckdb -o edge_report.tsv

        # From files
        koza edge-report -n nodes.tsv -e edges.tsv -o edge_report.parquet --format parquet

        # Custom columns
        koza edge-report -d merged.duckdb -o report.tsv \\
            -c subject_category -c predicate -c object_category -c primary_knowledge_source
    """
    try:
        if not database and not edge_file:
            raise typer.BadParameter("Must specify either --database or --edges")

        # Build config
        config_kwargs = {
            "output_file": Path(output) if output else None,
            "output_format": format,
            "quiet": quiet,
        }

        if database:
            db_path = Path(database)
            if not db_path.exists():
                raise typer.BadParameter(f"Database file not found: {database}")
            config_kwargs["database_path"] = db_path
        else:
            if edge_file:
                edge_path = Path(edge_file)
                if not edge_path.exists():
                    raise typer.BadParameter(f"Edge file not found: {edge_file}")
                config_kwargs["edge_file"] = FileSpec(path=edge_path)

            if node_file:
                node_path = Path(node_file)
                if not node_path.exists():
                    raise typer.BadParameter(f"Node file not found: {node_file}")
                config_kwargs["node_file"] = FileSpec(path=node_path)

        if columns:
            config_kwargs["categorical_columns"] = columns

        config = EdgeReportConfig(**config_kwargs)
        result = generate_edge_report(config)

        if not quiet:
            typer.echo("✓ Edge report generated successfully")
            if result.output_file:
                typer.echo(f"Report saved to: {result.output_file}")

    except Exception as e:
        typer.echo(f"Error generating edge report: {e}", err=True)
        raise typer.Exit(1)


@typer_app.command(name="node-examples")
def node_examples_cmd(
    database: Annotated[
        str | None, typer.Option("--database", "-d", help="Path to DuckDB database file")
    ] = None,
    node_file: Annotated[
        str | None, typer.Option("--file", "-f", help="Path to node file (TSV, JSONL, or Parquet)")
    ] = None,
    output: Annotated[str, typer.Option("--output", "-o", help="Path to output examples file")] = None,
    format: Annotated[
        TabularReportFormat, typer.Option("--format", help="Output format")
    ] = TabularReportFormat.TSV,
    sample_size: Annotated[
        int, typer.Option("--sample-size", "-n", help="Number of examples per type")
    ] = 5,
    type_column: Annotated[
        str, typer.Option("--type-column", "-t", help="Column to partition examples by")
    ] = "category",
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress progress output")] = False,
):
    """
    Generate sample rows per node type.

    Samples N example rows for each distinct value in the type column (default: category).

    Examples:

        # From database (5 examples per category)
        koza node-examples -d merged.duckdb -o node_examples.tsv

        # From file with 10 examples per type
        koza node-examples -f nodes.tsv -o examples.tsv -n 10

        # Group by different column
        koza node-examples -d merged.duckdb -o examples.tsv -t provided_by
    """
    try:
        if not database and not node_file:
            raise typer.BadParameter("Must specify either --database or --file")

        # Build config
        config_kwargs = {
            "output_file": Path(output) if output else None,
            "output_format": format,
            "sample_size": sample_size,
            "type_column": type_column,
            "quiet": quiet,
        }

        if database:
            db_path = Path(database)
            if not db_path.exists():
                raise typer.BadParameter(f"Database file not found: {database}")
            config_kwargs["database_path"] = db_path
        else:
            file_path = Path(node_file)
            if not file_path.exists():
                raise typer.BadParameter(f"Node file not found: {node_file}")
            config_kwargs["node_file"] = FileSpec(path=file_path)

        config = NodeExamplesConfig(**config_kwargs)
        result = generate_node_examples(config)

        if not quiet:
            typer.echo("✓ Node examples generated successfully")
            if result.output_file:
                typer.echo(f"Examples saved to: {result.output_file}")

    except Exception as e:
        typer.echo(f"Error generating node examples: {e}", err=True)
        raise typer.Exit(1)


@typer_app.command(name="edge-examples")
def edge_examples_cmd(
    database: Annotated[
        str | None, typer.Option("--database", "-d", help="Path to DuckDB database file")
    ] = None,
    node_file: Annotated[
        str | None, typer.Option("--nodes", "-n", help="Path to node file (for denormalization)")
    ] = None,
    edge_file: Annotated[
        str | None, typer.Option("--edges", "-e", help="Path to edge file (TSV, JSONL, or Parquet)")
    ] = None,
    output: Annotated[str, typer.Option("--output", "-o", help="Path to output examples file")] = None,
    format: Annotated[
        TabularReportFormat, typer.Option("--format", help="Output format")
    ] = TabularReportFormat.TSV,
    sample_size: Annotated[
        int, typer.Option("--sample-size", "-s", help="Number of examples per type")
    ] = 5,
    type_columns: Annotated[
        list[str] | None,
        typer.Option("--type-column", "-t", help="Columns to partition examples by (can specify multiple)"),
    ] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress progress output")] = False,
):
    """
    Generate sample rows per edge type.

    Samples N example rows for each distinct combination of type columns
    (default: subject_category, predicate, object_category).

    Examples:

        # From database (5 examples per edge type)
        koza edge-examples -d merged.duckdb -o edge_examples.tsv

        # From files with 10 examples
        koza edge-examples -n nodes.tsv -e edges.tsv -o examples.tsv -s 10

        # Custom type columns
        koza edge-examples -d merged.duckdb -o examples.tsv -t predicate -t primary_knowledge_source
    """
    try:
        if not database and not edge_file:
            raise typer.BadParameter("Must specify either --database or --edges")

        # Build config
        config_kwargs = {
            "output_file": Path(output) if output else None,
            "output_format": format,
            "sample_size": sample_size,
            "quiet": quiet,
        }

        if type_columns:
            config_kwargs["type_columns"] = type_columns

        if database:
            db_path = Path(database)
            if not db_path.exists():
                raise typer.BadParameter(f"Database file not found: {database}")
            config_kwargs["database_path"] = db_path
        else:
            if edge_file:
                edge_path = Path(edge_file)
                if not edge_path.exists():
                    raise typer.BadParameter(f"Edge file not found: {edge_file}")
                config_kwargs["edge_file"] = FileSpec(path=edge_path)

            if node_file:
                node_path = Path(node_file)
                if not node_path.exists():
                    raise typer.BadParameter(f"Node file not found: {node_file}")
                config_kwargs["node_file"] = FileSpec(path=node_path)

        config = EdgeExamplesConfig(**config_kwargs)
        result = generate_edge_examples(config)

        if not quiet:
            typer.echo("✓ Edge examples generated successfully")
            if result.output_file:
                typer.echo(f"Examples saved to: {result.output_file}")

    except Exception as e:
        typer.echo(f"Error generating edge examples: {e}", err=True)
        raise typer.Exit(1)


@typer_app.command()
def validate(
    database: Annotated[str, typer.Option("--database", "-d", help="Path to DuckDB database file")],
    output: Annotated[
        str | None, typer.Option("--output", "-o", help="Path to output validation report (YAML)")
    ] = None,
    schema: Annotated[
        str | None, typer.Option("--schema", "-s", help="Path to custom LinkML schema (defaults to Biolink)")
    ] = None,
    sample_limit: Annotated[
        int, typer.Option("--samples", "-n", help="Number of violation samples to include")
    ] = 10,
    errors_only: Annotated[
        bool, typer.Option("--errors-only", help="Only report errors, not warnings")
    ] = False,
    profile: Annotated[
        str, typer.Option("--profile", "-p", help="Validation profile: minimal, standard, or full")
    ] = "standard",
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress progress output")] = False,
):
    """
    Validate a graph database against Biolink model constraints.

    Runs declarative validation using SQL queries generated from LinkML schema
    constraints. Reports violations with counts and sample records.

    Validation includes:
    - Schema structure (missing required/recommended columns)
    - Required fields (NULL checks for existing columns)
    - Recommended fields (NULL checks with warning severity)
    - Referential integrity (edge subjects/objects exist in nodes)
    - Biolink categories (valid category values)
    - Biolink predicates (valid predicate values)
    - ID prefix validation (IDs match expected prefixes for category)
    - Predicate hierarchy (predicates exist in Biolink slot hierarchy)

    Examples:

        # Basic validation
        koza validate -d merged.duckdb -o validation_report.yaml

        # With custom schema
        koza validate -d merged.duckdb -s custom-biolink.yaml

        # Errors only, more samples
        koza validate -d merged.duckdb --errors-only --samples 50
    """
    try:
        database_path = Path(database)
        if not database_path.exists():
            raise typer.BadParameter(f"Database file not found: {database}")

        if not quiet:
            print(f"Validating {database_path.name} against Biolink model...")

        config = ValidationConfig(
            database_path=database_path,
            output_file=Path(output) if output else None,
            schema_path=schema,
            sample_limit=sample_limit,
            include_warnings=not errors_only,
            include_info=False,
            quiet=quiet,
            profile=profile,
        )

        result = validate_graph(config)

        if not quiet:
            _print_validation_summary(result)
            if result.output_file:
                print(f"Validation report written to {result.output_file}")

    except Exception as e:
        typer.echo(f"Error during validation: {e}", err=True)
        raise typer.Exit(1)


def _print_validation_summary(result):
    """Print validation summary to console."""
    report = result.validation_report
    print(f"\nValidation Summary:")
    print(f"  Compliance: {report.compliance_percentage:.1f}%")
    print(f"  Errors: {report.error_count}")
    print(f"  Warnings: {report.warning_count}")
    print(f"  Tables validated: {', '.join(report.tables_validated)}")

    if report.violations:
        print(f"\nTop violations:")
        sorted_violations = sorted(report.violations, key=lambda x: x.violation_count, reverse=True)[:5]
        for v in sorted_violations:
            print(f"  - [{v.severity}] {v.slot_name} ({v.table}): {v.violation_count} violations")
            print(f"    {v.description}")


if __name__ == "__main__":
    typer_app()
