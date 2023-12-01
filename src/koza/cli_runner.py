"""
Module for managing koza runs through the CLI
"""

from pathlib import Path
from typing import Dict, Optional, Union
import yaml

from koza.app import KozaApp
from koza.io.reader.csv_reader import CSVReader
from koza.io.reader.json_reader import JSONReader
from koza.io.reader.jsonl_reader import JSONLReader
from koza.io.utils import open_resource
from koza.io.yaml_loader import UniqueIncludeLoader
from koza.model.config.source_config import FormatType, OutputFormat, PrimaryFileConfig
from koza.model.source import Source
from koza.model.translation_table import TranslationTable
from koza.utils.log_utils import get_logger

global koza_apps
koza_apps = {}


def get_koza_app(source_name) -> Optional[KozaApp]:
    """Return a KozaApp object for a given source

    Args:
        source_name (str): Name of source
    """
    try:
        return koza_apps[source_name]
    except:
        raise KeyError(f"{source_name} was not found in KozaApp dictionary")


def transform_source(
    source: str,
    output_dir: str,
    output_format: OutputFormat = OutputFormat('tsv'),
    global_table: str = None,
    local_table: str = None,
    schema: str = None,
    node_type: str = None,
    edge_type: str = None,
    row_limit: int = None,
    verbose: bool = None,
    log: bool = False,
):
    """Create a KozaApp object, process maps, and run the transform

    Args:
        source (str): Path to source metadata file
        output_dir (str): Path to output directory
        output_format (OutputFormat, optional): Output format. Defaults to OutputFormat('tsv').
        global_table (str, optional): Path to global translation table. Defaults to None.
        local_table (str, optional): Path to local translation table. Defaults to None.
        schema (str, optional): Path to schema file. Defaults to None.
        row_limit (int, optional): Number of rows to process. Defaults to None.
        verbose (bool, optional): Verbose logging. Defaults to None.
        log (bool, optional): Log to file. Defaults to False.
    """
    logger = get_logger(name=Path(source).name if log else None, verbose=verbose)

    with open(source, 'r') as source_fh:
        source_config = PrimaryFileConfig(**yaml.load(source_fh, Loader=UniqueIncludeLoader))

    if not source_config.name:
        source_config.name = Path(source).stem

    if not source_config.transform_code:
        # look for it alongside the source conf as a .py file
        source_config.transform_code = str(Path(source).parent / Path(source).stem) + '.py'

    koza_source = Source(source_config, row_limit)
    logger.debug(f"Source created: {koza_source.config.name}")
    translation_table = get_translation_table(
        global_table if global_table else source_config.global_table,
        local_table if local_table else source_config.local_table,
        logger,
    )

    koza_app = _set_koza_app(
        koza_source, translation_table, output_dir, output_format, schema, node_type, edge_type, logger
    )
    koza_app.process_maps()
    koza_app.process_sources()


def validate_file(
    file: str,
    format: FormatType = FormatType.csv,
    delimiter: str = ',',
    header_delimiter: str = None,
    skip_blank_lines: bool = True,
):
    """
    Runs a file through one of the Koza readers
    For csv files will return header and row length

    For json and jsonl just validates them
    """

    with open_resource(file) as resource_io:
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


def get_translation_table(
    global_table: Union[str, Dict] = None,
    local_table: Union[str, Dict] = None,
    logger=None,
) -> TranslationTable:
    """Create a translation table object from two file paths

    Args:
        global_table (str, optional): Path to global translation table. Defaults to None.
        local_table (str, optional): Path to local translation table. Defaults to None.

    Returns:
        TranslationTable: TranslationTable object
    """

    global_tt = {}
    local_tt = {}

    if not global_table:
        if local_table:
            raise ValueError("Local table without a global table not allowed")
        else:
            logger.debug("No global table used for transform")
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
            logger.debug("No local table used for transform")

    return TranslationTable(global_tt, local_tt)


def _set_koza_app(
    source: Source,
    translation_table: TranslationTable = None,
    output_dir: str = './output',
    output_format: OutputFormat = OutputFormat('tsv'),
    schema: str = None,
    node_type: str = None,
    edge_type: str = None,
    logger=None,
) -> KozaApp:
    """Create a KozaApp object for a given source"""

    koza_apps[source.config.name] = KozaApp(
        source, translation_table, output_dir, output_format, schema, node_type, edge_type, logger
    )
    logger.debug(f"koza_apps entry created for {source.config.name}: {koza_apps[source.config.name]}")
    return koza_apps[source.config.name]


def test_koza(koza: KozaApp):
    """Manually sets KozaApp (for testing)"""
    global koza_app
    koza_app = koza
