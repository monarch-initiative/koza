"""
Module for managing koza runs
"""

import logging
from pathlib import Path
from typing import Optional

import yaml

from koza.io.reader.csv_reader import CSVReader
from koza.io.reader.json_reader import JSONReader
from koza.io.reader.jsonl_reader import JSONLReader
from koza.io.utils import open_resource
from koza.koza import KozaApp
from koza.model.config.source_config import CompressionType, FormatType, SourceConfig
from koza.model.source import Source
from koza.model.translation_table import TranslationTable

LOG = logging.getLogger(__name__)

KOZA_APP = None


def set_koza_app(
    source: Source,
    config_dir: str = './',
    output_dir: str = './output',
    curie_path: str = None,
) -> KozaApp:
    """
    Setter for singleton koza app object
    """
    global KOZA_APP

    KOZA_APP = KozaApp(source, config_dir, output_dir, curie_path)
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
    source_path = Path(f"{config_dir}/sources/{source}")
    if not (source_path.exists() or source_path.is_dir()):
        # maybe config is the whole path
        alt_path = Path(f"{config_dir}/{source}")

        if not (alt_path.exists() or alt_path.is_dir()):
            raise FileNotFoundError(f"source directory does not exist, {source_path}")

        source_path = alt_path

    return source_path


def get_translation_table(source: str, config_dir: str) -> TranslationTable:
    # Look for translation table files
    global_tt_path = Path(f"{config_dir}/translationtable/GLOBAL_TERMS.yaml")
    local_tt_path = Path(f"{config_dir}/translationtable/{source}.yaml")

    if not global_tt_path.exists():
        LOG.warning("Global translation table does not exist")
        global_tt = {}
    else:
        with global_tt_path.open('r') as global_tt_fh:
            global_tt = yaml.safe_load(global_tt_fh)

    if not local_tt_path.exists():
        LOG.warning("Source translation table does not exist")
        local_tt = {}
    else:
        with local_tt_path.open('r') as local_tt_fh:
            local_tt = yaml.safe_load(local_tt_fh)

    return TranslationTable(global_tt, local_tt)


def transform_source(
    source: str,
    config_dir: str,
    output_dir: str,
    curie_map: str = None,
):
    source_path = resolve_source(source, config_dir)
    source_metadata = source_path / 'metadata.yaml'

    translation_table = get_translation_table(source, config_dir)

    with source_metadata.open('r') as source_fh:
        source_config = SourceConfig(**yaml.safe_load(source_fh))
        if not source_config.name:
            source_config.name = source

        source = Source(
            source_files=source_config.source_files,
            name=source_config.name,
            data_dir=source_config.data_dir,
            dataset_description=source_config.dataset_description,
            translation_table=translation_table,
        )

        set_koza_app(source, config_dir, output_dir, curie_map)
