"""
Module for managing koza runs through the CLI
"""

from pathlib import Path
from typing import Dict, Literal, Optional, Union
import yaml

import duckdb

from koza.app import KozaApp
from koza.io.reader.csv_reader import CSVReader
from koza.io.reader.json_reader import JSONReader
from koza.io.reader.jsonl_reader import JSONLReader
from koza.io.utils import open_resource
from koza.io.yaml_loader import UniqueIncludeLoader
from koza.model.config.source_config import FormatType, OutputFormat, PrimaryFileConfig
from koza.model.source import KozaSource
from koza.model.translation_table import TranslationTable
from koza.utils.log_utils import get_logger

global koza_apps
koza_apps = {}


def get_koza_app(source_name) -> Optional[KozaApp]:
    """Return a KozaApp object for a given source_name, if this app was
    already built and constructed by _build_and_set_koza_app.

    Args:
        source_name (str): Name of source
    """
    try:
        return koza_apps[source_name]
    except KeyError:
        raise KeyError(f"{source_name} was not found in KozaApp dictionary")


def transform_source(
    source: str,
    output_dir: str,
    output_format: OutputFormat = OutputFormat("tsv"),
    global_table: str = None,
    local_table: str = None,
    schema: str = None,
    node_type: str = None,
    edge_type: str = None,
    row_limit: int = None,
    verbose: bool = None,
    log: bool = False,
):
    """Create a KozaSource object. Use that KozaSource object to make
    a KozaApp, and run the transform. This will be the primary entry

    Args:
        source (str): Path to source metadata yaml file. (Format described https://koza.monarchinitiative.org/Ingests/source_config/)
        output_dir (str): Path to output directory
        output_format (OutputFormat, optional): Output format. Defaults to OutputFormat('tsv').
        global_table (str, optional): Path to global translation table. Defaults to None.
        local_table (str, optional): Path to local translation table. Defaults to None.
        schema (str, optional): Path to schema file. Defaults to None.
        row_limit (int, optional): Number of rows to process. Defaults to None.
        verbose (bool, optional): Verbose logging. Defaults to None.
        log (bool, optional): Log to file. Defaults to False.
    """
    koza_source = build_koza_source(source)
    logger = get_logger(name=Path(source).name if log else None, verbose=verbose)

    logger.debug(f"Source created: {koza_source.config.name}")
    translation_table = get_translation_table(
        global_table if global_table else source_config.global_table,
        local_table if local_table else source_config.local_table,
        logger,
    )

    koza_app = _build_and_set_koza_app(
        koza_source, translation_table, output_dir, output_format, schema, node_type, edge_type, logger
    )
    
    koza_app.process_maps()
    koza_app.process_sources()


def build_koza_source(
        source : str,
        row_limit : int = None
) -> KozaSource:
    """Create a KozaSource object. Use that KozaSource object to make
    a KozaApp, and run the transform. The bulk of this function is checks to ensure
    the location of the python code representing the transformation code is properly formatted
    and exists.

    Args:
        source (str): Path to source metadata yaml file which represents the ingest process.
        row_limit (int, optional): Number of rows to process. Defaults to None.
    """
    with open(source, "r") as source_fh:
        source_config = PrimaryFileConfig(**yaml.load(source_fh, Loader=UniqueIncludeLoader))

    # Set name and transform code if not provided
    if not source_config.name:
        source_config.name = Path(source).stem

    if not source_config.transform_code_location:
        filename = f"{Path(source).parent / Path(source).stem}.py"
        if not Path(filename).exists():
            filename = Path(source).parent / "transform.py"
        if not Path(filename).exists():
            raise FileNotFoundError(f"Could not find transform file for {source}")
        source_config.transform_code_location = filename

    koza_source = Source(source_config, row_limit)
    return koza_source

def run_qc(
        koza_app : KozaApp,
        koza_source : KozaSource
):
    """Takes in a constructed KozaApp and KozaSource object; a
    transformations described in the KozaApp and run quality control
    protocols based upon the KozaSource.

    Args:
        koza_app (KozaApp): The KozaApp object which has had "process_maps()" and "process_sources()" run.
        koza_source (KozaSource): The KozaSource object used to build the KozaApp object, for QC.
    """
    
    ### QC checks

    def _check_row_count(type: Literal["node", "edge"]):
        """Check row count for nodes or edges."""

        if type == "node":
            outfile = koza_app.node_file
            min_count = source_config.min_node_count
        elif type == "edge":
            outfile = koza_app.edge_file
            min_count = source_config.min_edge_count

        count = duckdb.sql(f"SELECT count(*) from '{outfile}' as count").fetchone()[0]

        if row_limit and row_limit < min_count:
            logger.warning(f"Row limit '{row_limit}' is less than expected count of {min_count} {type}s")
        elif row_limit and row_limit < count:
            logger.error(f"Actual {type} count {count} exceeds row limit {row_limit}")
        else:
            if count < min_count * 0.7:
                raise ValueError(f"Actual {type} count {count} is less than 70% of expected {min_count} {type}s")
            if min_count * 0.7 <= count < min_count:
                logger.warning(
                    f"Actual {type} count {count} is less than expected {min_count}, but more than 70% of expected"
                )

    # Confirm min number of rows in output
    if hasattr(koza_app, "node_file") and source_config.min_node_count is not None:
        _check_row_count("node")

    if hasattr(koza_app, "edge_file") and source_config.min_edge_count is not None:
        _check_row_count("edge")
                           
def build_koza_app_from_source(
        koza_source : KozaSource 
):
    """Create a KozaApp object.

    Args:
        koza_source (KozaSource): A KozaSource object representing the 
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

    with open(source, "r") as source_fh:
        source_config = PrimaryFileConfig(**yaml.load(source_fh, Loader=UniqueIncludeLoader))

    # Set name and transform code location if not provided
    if not source_config.name:
        source_config.name = Path(source).stem

    if not source_config.transform_code_location:
        filename = f"{Path(source).parent / Path(source).stem}.py"
        if not Path(filename).exists():
            filename = Path(source).parent / "transform.py"
        if not Path(filename).exists():
            raise FileNotFoundError(f"Could not find transform file for {source}")
        source_config.transform_code_location = filename

    koza_source = Source(source_config, row_limit)
    logger.debug(f"Source created: {koza_source.config.name}")

    #Build a translation table. If 
    translation_table = get_translation_table(
        global_table if global_table else source_config.global_table,
        local_table if local_table else source_config.local_table,
        logger,
    )

    koza_app = _build_and_set_koza_app(
        koza_source, translation_table, output_dir, output_format, schema, node_type, edge_type, logger
    )
    return koza_app

def validate_file(
    file: str,
    format: FormatType = FormatType.csv,
    delimiter: str = ",",
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
            with open(global_table, "r") as global_tt_fh:
                global_tt = yaml.safe_load(global_tt_fh)
        elif isinstance(global_table, Dict):
            global_tt = global_table

        if local_table:
            if isinstance(local_table, str):
                with open(local_table, "r") as local_tt_fh:
                    local_tt = yaml.safe_load(local_tt_fh)
            elif isinstance(local_table, Dict):
                local_tt = local_table

        else:
            logger.debug("No local table used for transform")

    return TranslationTable(global_tt, local_tt)


def _build_and_set_koza_app(
    koza_source: KozaSource,
    translation_table: TranslationTable = None,
    output_dir: str = "./output",
    output_format: OutputFormat = OutputFormat("tsv"),
    schema: str = None,
    node_type: str = None,
    edge_type: str = None,
    logger=None,
) -> KozaApp:
    """Create a KozaApp object for a given source"""

    koza_apps[source.config.name] = KozaApp(
        koza_source, translation_table, output_dir, output_format, schema, node_type, edge_type, logger
    )
    logger.debug(f"koza_apps entry created for {source.config.name}: {koza_apps[source.config.name]}")
    return koza_apps[source.config.name]
