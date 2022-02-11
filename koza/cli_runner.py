"""
Module for managing koza runs through the CLI
"""

import logging
from pathlib import Path
from typing import Optional, Union, Dict

import yaml

from koza.app import KozaApp
from koza.io.reader.csv_reader import CSVReader
from koza.io.reader.json_reader import JSONReader
from koza.io.reader.jsonl_reader import JSONLReader
from koza.io.utils import open_resource
from koza.io.yaml_loader import UniqueIncludeLoader
from koza.model.config.source_config import (
    CompressionType,
    FormatType,
    OutputFormat,
    PrimaryFileConfig,
)
from koza.model.source import Source
from koza.model.translation_table import TranslationTable

LOG = logging.getLogger(__name__)

koza_app = None


def set_koza(koza: KozaApp):
    global koza_app
    koza_app = koza


def set_koza_app(
    source: Source,
    translation_table: TranslationTable = None,
    output_dir: str = './output',
    output_format: OutputFormat = OutputFormat('tsv'),
) -> KozaApp:
    """
    Setter for singleton koza app object
    """
    global koza_app

    koza_app = KozaApp(source, translation_table, output_dir, output_format)
    return koza_app


def get_koza_app() -> Optional[KozaApp]:
    """
    Getter for singleton koza app object
    """
    return koza_app


def validate_file(
    file: str,
    format: FormatType = FormatType.csv,
    delimiter: str = ',',
    header_delimiter: str = None,
    compression: CompressionType = None,
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


def get_translation_table(global_table: Union[str, Dict] = None, local_table: Union[str, Dict] = None) -> TranslationTable:
    """
    Create a translation table object from two file paths
    :param global_table: str, path to global table yaml
    :param local_table: str, path to local table yaml
    :return: TranslationTable
    """

    global_tt = {}
    local_tt = {}

    if not global_table:
        if local_table:
            raise ValueError("Local table without a global table not allowed")
        else:
            LOG.info("No global table used for transform")
    else:

        if isinstance(global_table, str):
            with open(global_table, 'r') as global_tt_fh:
                global_tt = yaml.safe_load(global_tt_fh)
        elif isinstance(global_table, Dict):
            global_tt = global_table

        if local_table:
            if isinstance(local_table, str):
                with open(local_table, 'r') as local_tt_fh:
                    local_tt = yaml.safe_load(local_tt_fh)
            elif isinstance(local_table, Dict):
                local_tt = local_table

        else:
            LOG.info("No local table used for transform")

    return TranslationTable(global_tt, local_tt)


def transform_source(
    source: str,
    output_dir: str,
    output_format: OutputFormat = OutputFormat('tsv'),
    global_table: str = None,
    local_table: str = None,
    row_limit: int = None
):

    with open(source, 'r') as source_fh:
        source_config = PrimaryFileConfig(**yaml.load(source_fh, Loader=UniqueIncludeLoader))
        if not source_config.name:
            source_config.name = Path(source).stem

        if not source_config.transform_code:
            # look for it alongside the source conf as a .py file
            source_config.transform_code = str(Path(source).parent / Path(source).stem) + '.py'

        koza_source = Source(source_config, row_limit)

        translation_table = get_translation_table(global_table if global_table else source_config.global_table,
                                                  local_table if local_table else source_config.local_table)

        koza_app = set_koza_app(koza_source, translation_table, output_dir, output_format)
        koza_app.process_maps()
        koza_app.process_sources()
