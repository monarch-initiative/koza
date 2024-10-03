"""
Module for managing koza runs through the CLI
"""

from pathlib import Path
import os
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

    with open(source, "r") as source_fh:
        source_config = PrimaryFileConfig(**yaml.load(source_fh, Loader=UniqueIncludeLoader))

    # Set name and transform code if not provided
    if not source_config.name:
        source_config.name = Path(source).stem

    if not source_config.transform_code:
        filename = f"{Path(source).parent / Path(source).stem}.py"
        if not Path(filename).exists():
            filename = Path(source).parent / "transform.py"
        if not Path(filename).exists():
            raise FileNotFoundError(f"Could not find transform file for {source}")
        source_config.transform_code = filename

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


def split_file(file: str,
               fields: str,
               format: OutputFormat = OutputFormat.tsv,
               remove_prefixes: bool = False,
               output_dir: str = "./output"):
    db = duckdb.connect(":memory:")

    #todo: validate that each of the fields is actually a column in the file
    if format == OutputFormat.tsv:
        read_file = f"read_csv('{file}')"
    elif format == OutputFormat.json:
        read_file = f"read_json('{file}')"
    else:
        raise ValueError(f"Format {format} not supported")

    values = db.execute(f'SELECT DISTINCT {fields} FROM {read_file};').fetchall()
    keys = fields.split(',')
    list_of_value_dicts = [dict(zip(keys, v)) for v in values]

    def clean_value_for_filename(value):
        if remove_prefixes and ':' in value:
            value = value.split(":")[-1]

        return value.replace("biolink:", "").replace(" ", "_").replace(":", "_")

    def generate_filename_from_row(row):
        return "_".join([clean_value_for_filename(row[k]) for k in keys if row[k] is not None])

    def get_filename_prefix(name):
        # get just the filename part of the path
        name = os.path.basename(name)
        if name.endswith('_edges.tsv'):
            return name[:-9]
        elif name.endswith('_nodes.tsv'):
            return name[:-9]
        else:
            raise ValueError(f"Unexpected file name {name}, not sure how to make am output prefix for it")

    def get_filename_suffix(name):
        if name.endswith('_edges.tsv'):
            return '_edges.tsv'
        elif name.endswith('_nodes.tsv'):
            return '_nodes.tsv'
        else:
            raise ValueError(f"Unexpected file name {name}, not sure how to make am output prefix for it")

    # create output/split if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    for row in list_of_value_dicts:
        # export to a tsv file named with the values of the pivot fields
        where_clause = ' AND '.join([f"{k} = '{row[k]}'" for k in keys])
        file_name = output_dir + "/" + get_filename_prefix(file) +  generate_filename_from_row(row) + get_filename_suffix(file)
        print(f"writing {file_name}")
        db.execute(f"""
        COPY (
            SELECT * FROM {read_file}
            WHERE {where_clause}
        ) TO '{file_name}' (HEADER, DELIMITER '\t');
        """)


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


def _set_koza_app(
    source: Source,
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
        source, translation_table, output_dir, output_format, schema, node_type, edge_type, logger
    )
    logger.debug(f"koza_apps entry created for {source.config.name}: {koza_apps[source.config.name]}")
    return koza_apps[source.config.name]
