"""
Module for managing koza runs
"""

import logging
from pathlib import Path
from typing import List, Optional

import yaml

from koza.app import KozaApp
from koza.io.reader.csv_reader import CSVReader
from koza.io.reader.json_reader import JSONReader
from koza.io.reader.jsonl_reader import JSONLReader
from koza.io.utils import open_resource
from koza.model.config.source_config import CompressionType, FormatType, OutputFormat, SourceConfig
from koza.model.source import Source
from koza.model.translation_table import TranslationTable

LOG = logging.getLogger(__name__)

KOZA_APP = None


def set_koza(koza: KozaApp):
    global KOZA_APP
    KOZA_APP = koza


def set_koza_app(
    source: Source,
    output_dir: str = './output',
    output_format: OutputFormat = OutputFormat('jsonl'),
) -> KozaApp:
    """
    Setter for singleton koza app object
    """
    global KOZA_APP

    KOZA_APP = KozaApp(source, output_dir, output_format)
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


def validate_source_files(source: str, source_files: List[str]) -> List[str]:
    """
    Resolve a source string to its source metadata file

    :param source:
    :param source_files:
    :return:
    """
    source_dir = Path(source).parent
    source_paths = []
    for src_file in source_files:
        if not (Path(src_file).exists() or Path(src_file).is_file()):
            # check if it's in source parent
            updated_src_file = source_dir / src_file
            if not (Path(updated_src_file).exists() or Path(updated_src_file).is_file()):
                raise ValueError(f"Source file doesn't exist: {src_file}")
            else:
                source_paths.append(updated_src_file)
        else:
            source_paths.append(src_file)
    return source_paths


def get_translation_table(global_table: str, local_table: str) -> TranslationTable:
    # Look for translation table files

    global_tt = {}
    local_tt = {}

    if not global_table:
        if local_table:
            raise ValueError("Local table without a global table not allowed")
        else:
            LOG.info("No global table used for transform")
    else:

        with open(global_table, 'r') as global_tt_fh:
            global_tt = yaml.safe_load(global_tt_fh)

        if local_table:
            with open(local_table, 'r') as local_tt_fh:
                local_tt = yaml.safe_load(local_tt_fh)
        else:
            LOG.info("No local table used for transform")

    return TranslationTable(global_tt, local_tt)


def transform_source(
    source: str,
    output_dir: str,
    output_format: OutputFormat,
    global_table: str,
    local_table: str,
):

    translation_table = get_translation_table(global_table, local_table)

    with open(source, 'r') as source_fh:
        source_config = SourceConfig(**yaml.safe_load(source_fh))
        if not source_config.name:
            source_config.name = Path(source).stem

        source = Source(
            source_files=validate_source_files(source, source_config.source_files),
            name=source_config.name,
            dataset_description=source_config.dataset_description,
            translation_table=translation_table,
        )

        koza_app = set_koza_app(source, output_dir, output_format)
        koza_app.process_sources()
