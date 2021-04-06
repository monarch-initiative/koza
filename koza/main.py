#!/usr/bin/env python3

import logging
import uuid
from pathlib import Path

from typing import List
import typer

from koza.koza_runner import run_single_resource
from koza.model.config.koza_config import SerializationEnum
from koza.model.config.source_config import CompressionType, FormatType, ColumnFilter

app = typer.Typer()


logging.basicConfig()
LOG = logging.getLogger(__name__)


@app.command()
def run(
    file: str = typer.Option(..., help="Path or url to the source file"),
    format: FormatType = FormatType.csv,
    delimiter: str = ',',
    header_delimiter: str = None,
    filters: List[ColumnFilter] = None,
    compression: CompressionType = None,
    output: str = None,
    output_format: SerializationEnum = SerializationEnum.tsv,
    quiet: bool = False,
    debug: bool = False,
):
    """
    Run a single file through koza
    """
    _set_log_level(quiet, debug)

    if output is None:

        if output_format == SerializationEnum.tsv:
            extension = 'tsv'
        else:
            extension = 'tsv'

        filename = str(uuid.uuid4()) + '.' + extension
        output_directory = Path("/tmp")
        output_directory.mkdir(parents=True, exist_ok=True)
        output_fp = output_directory / filename
        output = open(output_fp, 'w')

        LOG.warning(f"No output file provided, writing to {output_fp}")

    # If a user passes in \s for a space delimited csv file
    if delimiter == '\\s':
        delimiter = ' '
    run_single_resource(file, format, delimiter, header_delimiter, output, filters, compression)


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
