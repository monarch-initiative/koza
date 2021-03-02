#!/usr/bin/env python3

import logging

import typer

from koza.model.config.source_config import FormatType, CompressionType
from koza.koza_runner import run_single_resource

app = typer.Typer()


logging.basicConfig()
LOG = logging.getLogger(__name__)


@app.command()
def run(
        file: str = typer.Option(..., help="Path or url to the source file"),
        format: FormatType = FormatType.csv,
        delimiter: str = ',',
        header_delimiter: str = None,
        filter: str = None,
        compression: CompressionType = None,
        quiet: bool = False,
        debug: bool = False
):
    """
    Run a single file through koza
    """

    # Logging levels
    if quiet:
        logging.getLogger().setLevel(logging.WARNING)
    elif debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    # If a user passes in \s for a space delimited csv file
    if delimiter == '\\s':
        delimiter = ' '
    run_single_resource(file, format, delimiter, header_delimiter, filter, compression)
    #typer.echo(f"Creating item: {name}")


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


if __name__ == "__main__":
    app()
