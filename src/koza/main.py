#!/usr/bin/env python3
"""CLI for Koza - wraps the koza library to provide a command line interface"""

from pathlib import Path
from typing import Optional

from koza.cli_runner import transform_source, validate_file
from koza.model.config.source_config import FormatType, OutputFormat

import typer

typer_app = typer.Typer()


@typer_app.callback(invoke_without_command=True)
def callback(version: Optional[bool] = typer.Option(None, "--version", is_eager=True)):
    if version:
        from koza import __version__

        typer.echo(f"Koza version: {__version__}")
        raise typer.Exit()


@typer_app.command()
def transform(
    source: str = typer.Option(..., help="Source metadata file"),
    output_dir: str = typer.Option('./output', help="Path to output directory"),
    output_format: OutputFormat = typer.Option("tsv", help="Output format"),
    global_table: str = typer.Option(None, help="Path to global translation table"),
    local_table: str = typer.Option(None, help="Path to local translation table"),
    schema: str = typer.Option(None, help='Path to schema YAML for validation in writer'),
    row_limit: int = typer.Option(None, help="Number of rows to process (if skipped, processes entire source file)"),
    verbose: Optional[bool] = typer.Option(None, "--debug/--quiet"),
    log: bool = typer.Option(False, help='Optional log mode - set true to save output to ./logs'),
) -> None:
    """Transform a source file"""

    output_path = Path(output_dir)

    if output_path.exists() and not output_path.is_dir():
        raise NotADirectoryError(f"{output_dir} is not a directory")
    elif not output_path.exists():
        output_path.mkdir(parents=True)

    transform_source(source, output_dir, output_format, global_table, local_table, schema, row_limit, verbose, log)


@typer_app.command()
def validate(
    file: str = typer.Option(..., help="Path or url to the source file"),
    format: FormatType = FormatType.csv,
    delimiter: str = ',',
    header_delimiter: str = None,
    skip_blank_lines: bool = True,
) -> None:
    """Validate a source file"""
    validate_file(file, format, delimiter, header_delimiter, skip_blank_lines)


# @typer_app.command()
# def create():
#    """
#    TODO
#    Create a new koza project
#    """

# if __name__ == "__main__":
#     typer_app()
