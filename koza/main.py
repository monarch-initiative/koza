#!/usr/bin/env python3

import logging
from pathlib import Path

import typer

from koza.koza_runner import run_single_resource
from koza.model.config.source_config import CompressionType, FormatType, OutputFormat

app = typer.Typer()


logging.basicConfig()
LOG = logging.getLogger(__name__)

"""
name: str = 'koza-run'
sources: List[str] = None
serialization: SerializationEnum = None
output: str = './'
config_dir: Union[str, Path] = './config'
cache_maps: bool = True
curie_map: Union[str, Path] = None
"""


@app.command()
def run(
    file: str = typer.Option(..., help="Path or url to the source file"),
    format: FormatType = FormatType.csv,
    delimiter: str = ',',
    header_delimiter: str = None,
    filter_file: str = None,
    compression: CompressionType = None,
    output_dir: str = None,
    output_format: OutputFormat = OutputFormat.tsv,
    quiet: bool = False,
    debug: bool = False,
):
    """
    Run a single file through koza
    """
    _set_log_level(quiet, debug)

    if output_dir is None:

        output_directory = Path("/tmp")
        output_directory.mkdir(parents=True, exist_ok=True)

        # LOG.warning(f"No output file provided, writing to {output_fp}")

    # If a user passes in \s for a space delimited csv file
    if delimiter == '\\s':
        delimiter = ' '
    run_single_resource(
        file,
        format,
        delimiter,
        header_delimiter,
        output_dir,
        output_format,
        filter_file,
        compression,
    )


@app.command()
def batch(item: str):
    """
    TODO
    Run a group of files through koza
    """


@app.command()
def create():
    """
    TODO
    Create a new koza project
    """


def _set_log_level(quiet: bool = False, debug: bool = False):
    if quiet:
        logging.getLogger().setLevel(logging.WARNING)
    elif debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)


if __name__ == "__main__":
    app()
