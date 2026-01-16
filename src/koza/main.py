#!/usr/bin/env python3
"""CLI for Koza - wraps the koza library to provide a command line interface"""

import glob as glob_module
from collections import defaultdict
from pathlib import Path
from typing import Annotated, Optional

import typer
from loguru import logger
from tqdm import tqdm

from koza.model.formats import InputFormat, OutputFormat
from koza.model.koza import KozaConfig
from koza.model.reader import CSVReaderConfig, JSONLReaderConfig, JSONReaderConfig, YAMLReaderConfig
from koza.model.transform import TransformConfig
from koza.model.writer import WriterConfig
from koza.runner import KozaRunner

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


def _expand_cli_file_patterns(patterns: list[str]) -> list[str]:
    """Expand glob patterns from CLI arguments and return a list of files.

    For each argument:
      * If it contains glob characters (``*``, ``?``, ``[]``) and matches files,
        the matching paths are expanded and added to the result in sorted order.
      * If it contains glob characters but matches no files, the original pattern
        is preserved and returned as a literal string.
      * If it contains no glob characters, it is treated as a literal path.

    The returned list is constructed in the same order as the input patterns,
    with matches for each glob pattern sorted individually.
    """
    expanded_files = []
    for pattern in patterns:
        # Check for glob characters
        if any(c in pattern for c in ["*", "?", "[", "]"]):
            matches = sorted(glob_module.glob(pattern, recursive=True))
            if matches:
                expanded_files.extend(matches)
            else:
                # If no glob matches, treat as literal filename
                expanded_files.append(pattern)
        else:
            expanded_files.append(pattern)
    return expanded_files


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
    input_files: Annotated[
        Optional[list[str]],
        typer.Option("--input-file", "-i", help="Input files or glob patterns (required for .py transforms)"),
    ] = None,
    input_format: Annotated[
        Optional[InputFormat],
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
) -> None:
    """Transform a source file.

    Accepts either a config YAML file or a Python transform file directly.

    Examples:
        # With config file (existing behavior)
        koza transform config.yaml

        # Config-free mode with transform file
        koza transform transform.py -i 'data/*.yaml'

        # With output options
        koza transform transform.py -i 'data/*.yaml' -f jsonl -o ./output

        # Explicit input format
        koza transform transform.py -i 'data/*.dat' --input-format yaml
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
            raise typer.BadParameter("--input-file/-i required when using a .py transform file")

        expanded_files = _expand_cli_file_patterns(input_files)
        # Note: expanded_files will always have at least the original patterns
        # (unmatched globs are preserved as literals), so validation happens
        # when files are opened rather than here.

        detected_format = input_format or _infer_input_format(expanded_files)

        # Create appropriate reader config based on format
        reader_configs = {
            InputFormat.yaml: YAMLReaderConfig,
            InputFormat.json: JSONReaderConfig,
            InputFormat.jsonl: JSONLReaderConfig,
            InputFormat.csv: CSVReaderConfig,
        }
        reader_config = reader_configs[detected_format](files=expanded_files)

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


# @typer_app.command()
# def validate(
#     file: str = typer.Option(..., help="Path or url to the source file"),
#     format: InputFormat = InputFormat.csv,
#     delimiter: str = ",",
#     header_delimiter: str = None,
#     skip_blank_lines: bool = True,
# ) -> None:
#     """Validate a source file"""
#     validate_file(file, format, delimiter, header_delimiter, skip_blank_lines)
#
#
# @typer_app.command()
# def split(
#     file: str = typer.Argument(..., help="Path to the source kgx file to be split"),
#     fields: str = typer.Argument(..., help="Comma separated list of fields to split on"),
#     remove_prefixes: bool = typer.Option(
#         False,
#         help=(
#             "Remove prefixes from the file names for values from the specified fields. "
#             "(e.g, NCBIGene:9606 becomes 9606).",
#         )
#     ),
#     output_dir: str = typer.Option(default="output", help="Path to output directory"),
# ):
#     """Split a file by fields"""
#     split_file(file, fields, remove_prefixes=remove_prefixes, output_dir=output_dir)


if __name__ == "__main__":
    typer_app()
