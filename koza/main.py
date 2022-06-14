#!/usr/bin/env python3
"""
CLI interface for Koza
"""

from pathlib import Path
import os
import typer

from koza.cli_runner import transform_source, validate_file
from koza.model.config.source_config import FormatType, OutputFormat

typer_app = typer.Typer()

import logging

logging.basicConfig()
# global LOG
# LOG = logging.getLogger(__name__)


@typer_app.command()
def transform(
    source: str = typer.Option(..., help="Source metadata file"),
    output_dir: str = typer.Option('./output', help="Path to output directory"),
    output_format: OutputFormat = typer.Option("tsv", help="Output format"),
    global_table: str = typer.Option(None, help="Path to global translation table"),
    local_table: str = typer.Option(None, help="Path to local translation table"),
    schema: str = typer.Option(None, help='Path to schema YAML for validation in writer'),
    row_limit: int = typer.Option(
        None, help="Number of rows to process (if skipped, processes entire source file)"
    ),
    quiet: bool = typer.Option(False, help="Optional quiet mode - set true to suppress output"),
    debug: bool = typer.Option(
        False, help="Optional debug mode - set true for additional debug output"
    ),
    log: bool = typer.Option(False, help='Optional log mode - set true to save output to ./logs'),
) -> None:
    """
    Transform a source file
    """
    # note: this requires koza users to follow the same dir structure, two levels of directories to find the .yaml file
    # else something like this might work with a generic directory structure:
    # os.path.basename(source) # name of the file + extension
    # os.path.dirname(source) # name of the directory
    # os.path.splitext(os.path.basename(source))[0] # name of the yaml file without the yaml
    logfile = Path(f"logs/{source.split('/')[1]}_{source.split('/')[2][:-5]}.log")
    if log:
        Path("logs").mkdir(parents=True, exist_ok=True)
    _set_log_level(quiet, debug, log, logfile)

    output_path = Path(output_dir)

    if output_path.exists() and not output_path.is_dir():
        raise NotADirectoryError(f"{output_dir} is not a directory")
    elif not output_path.exists():
        output_path.mkdir(parents=True)

    transform_source(
        source, output_dir, output_format, global_table, local_table, schema, row_limit
    )


@typer_app.command()
def validate(
    file: str = typer.Option(..., help="Path or url to the source file"),
    format: FormatType = FormatType.csv,
    delimiter: str = ',',
    header_delimiter: str = None,
    skip_blank_lines: bool = True,
):
    """
    Validate a source file

    Given a file and configuration checks that the file is valid, ie
    format is as expected (tsv, json), required columns/fields are there
    """
    _set_log_level(debug=True)

    validate_file(file, format, delimiter, header_delimiter, skip_blank_lines)


# @typer_app.command()
# def create():
#    """
#    TODO
#    Create a new koza project
#    """


def _set_log_level(
    quiet: bool = False, debug: bool = False, log: bool = False, logfile: str = 'logs/transform.log'
):

    if log:
        # Reset root logger in case it was configured elsewhere
        logger = logging.getLogger()
        logging.root.handlers = []

        # Set a handler for console output
        stream_handler = logging.StreamHandler()
        stream_formatter = logging.Formatter(':%(name)-20s: %(levelname)-8s: %(message)s')
        stream_handler.setFormatter(stream_formatter)
        stream_handler.setLevel(logging.WARNING)
        logger.addHandler(stream_handler)

        # Set a handler for file output
        file_handler = logging.FileHandler(logfile, mode='w')
        file_formatter = logging.Formatter("%(name)-26s: %(levelname)-8s: %(message)s")
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

        # Set root logger level
        logger.setLevel(logging.DEBUG)
    elif quiet:
        logging.getLogger().setLevel(logging.WARNING)
    elif debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)


if __name__ == "__main__":
    typer_app()
