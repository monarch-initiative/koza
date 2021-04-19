"""
Module for managing koza runs
"""

from pathlib import Path
from typing import IO, List, Optional

from koza.io.reader.csv_reader import CSVReader
from koza.io.reader.json_reader import JSONReader
from koza.io.reader.jsonl_reader import JSONLReader
from koza.io.utils import open_resource
from koza.model.config.source_config import CompressionType, FormatType

from .model.koza import KozaApp
from .model.source import Source, SourceFile

KOZA_APP = None


def set_koza_app(
    source: Source, source_files: List[SourceFile] = None, map_files: List[SourceFile] = None
) -> KozaApp:
    """
    Setter for singleton koza app object
    """
    global KOZA_APP

    KOZA_APP = KozaApp(source, source_files, map_files)
    return KOZA_APP


def get_koza_app() -> Optional[KozaApp]:
    """
    Getter for singleton koza app object
    """
    return KOZA_APP


def validate_file(
    file: str,
    format: FormatType = FormatType.csv,
    delimiter: str = ',',
    header_delimiter: str = None,
    compression: CompressionType = None,
    skip_lines: int = 0,
    skip_blank_lines: bool = True,
):
    """
    Runs a file through one of the Koza readers
    For csv files will return header and row length

    For json and jsonl just validates them
    """

    with open_resource(file, compression) as resource_io:

        if format == FormatType.csv:
            reader = CSVReader(
                resource_io,
                delimiter=delimiter,
                header_delimiter=header_delimiter,
                skip_lines=skip_lines,
                skip_blank_lines=skip_blank_lines,
            )
        elif format == FormatType.jsonl:
            reader = JSONLReader(resource_io)
        elif format == FormatType.json:
            reader = JSONReader(resource_io)
        else:
            raise ValueError

        for _ in reader:
            pass


def resolve_source(source: str, config_dir: str) -> Path:
    """
    Resolve a source string to its source metadata file

    :param source:
    :param config_dir:
    :return:
    """


def make_source(source_file: IO[str]) -> Source:
    pass


def transform_source(
    source: str,
    config_dir: str,
    output_dir: str,
    curie_map: str = None,
):
    pass
