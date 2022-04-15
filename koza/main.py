#!/usr/bin/env python3
"""
CLI interface for Koza
"""

from koza.cli_runner import transform_source, validate_file
from koza.model.config.source_config import FormatType, OutputFormat

import os
from pathlib import Path

import typer
typer_app = typer.Typer()

from contextlib import redirect_stdout
import logging, io
logging.basicConfig()
LOG = logging.getLogger(__name__)

@typer_app.command()
def transform(
    source: str = typer.Option(..., help="Source metadata file"),
    output_dir: str = typer.Option('./output', help="Path to output directory"),
    output_format: OutputFormat = typer.Option("tsv", help="Output format"),
    global_table: str = typer.Option(None, help="Path to global translation table"),
    local_table: str = typer.Option(None, help="Path to local translation table"),
    schema: str = typer.Option(None, help='Path to schema YAML for validation in writer'),
    row_limit: int = typer.Option(None, help="Number of rows to process (if skipped, processes entire source file)"),
    quiet: bool = typer.Option(False, help="Optional quiet mode - set true to suppress output"),
    debug: bool = typer.Option(False, help="Optional debug mode - set true for additional debug output"),
    log: bool = typer.Option(False, help='Optional log mode - set true to save output to ./logs')
) -> None:
    """
    Transform a source file
    """

    # Set logging specs
    #logfile = f"logs/{source.split('/')[1]}/{source.split('/')[2][:-5]}.log"
    logpath = os.path.join("logs", source.split("/")[1])
    Path(logpath).mkdir(parents=True, exist_ok=True)
    logfile = Path(f"{logpath}/{source.split('/')[2][:-5]}.log")
    _set_log_level(quiet, debug, log, logfile)

    output_path = Path(output_dir)

    if output_path.exists() and not output_path.is_dir():
        raise NotADirectoryError(f"{output_dir} is not a directory")
    elif not output_path.exists():
        output_path.mkdir(parents=True)

    # if log:
    #     logpath = os.path.join("logs", source.split("/")[1])
    #     Path(logpath).mkdir(parents=True, exist_ok=True)
    #     logfile = Path(f"{logpath}/{source.split('/')[2][:-5]}.log")
    #     if os.path.exists(logfile):
    #         os.remove(logfile)
    #     Path(logfile).touch()
    #     with open(outfile, 'w') as f:
    #         with redirect_stdout(f):
    #             transform_source(source, output_dir, output_format, global_table, local_table, schema, row_limit)
    #             return
    transform_source(source, output_dir, output_format, global_table, local_table, schema, row_limit)

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

    validate_file(
        file, format, delimiter, header_delimiter, skip_blank_lines
    )


# @typer_app.command()
# def create():
#    """
#    TODO
#    Create a new koza project
#    """


def _set_log_level(quiet: bool = False, debug: bool = False, log: bool = False, logfile: str = "logs/transform.log"):
    if log:
        
        # We stream the KGX logs to their own output to capture them
        # and also set up log output to a file which will accompany the transformed output
        log_stream = io.StringIO()
        log_handler = logging.StreamHandler(log_stream)
        log_file_handler = logging.FileHandler(logfile)
        log_handler.setLevel(logging.DEBUG)
        log_file_handler.setLevel(logging.DEBUG)
        #logging.basicConfig(filename=logfile, level=logging.INFO)
    elif quiet:
        logging.getLogger().setLevel(logging.WARNING)
    elif debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)


if __name__ == "__main__":
    typer_app()
