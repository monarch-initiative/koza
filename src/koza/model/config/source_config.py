"""
source config data class
map config data class
"""

import os
import tarfile
import zipfile
from dataclasses import field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Union, Optional
import yaml

from pydantic import StrictFloat, StrictInt, StrictStr
from pydantic.dataclasses import dataclass

from koza.model.config.pydantic_config import PYDANTIC_CONFIG
from koza.model.config.sssom_config import SSSOMConfig


class FilterCode(str, Enum):
    """Enum for filter codes (ex. gt = greater than)

    This should be aligned with https://docs.python.org/3/library/operator.html
    """

    gt = "gt"
    ge = "ge"
    lt = "lt"
    lte = "le"
    eq = "eq"
    ne = "ne"
    inlist = "in"
    inlist_exact = "in_exact"


class FilterInclusion(str, Enum):
    """Enum for filter inclusion/exclusion"""

    include = "include"
    exclude = "exclude"


class FieldType(str, Enum):
    """Enum for field types"""

    str = "str"
    int = "int"
    float = "float"


class FormatType(str, Enum):
    """Enum for supported file types"""

    csv = "csv"
    jsonl = "jsonl"
    json = "json"
    yaml = "yaml"
    # xml = "xml" # Not yet supported


class HeaderMode(str, Enum):
    """Enum for supported header modes in addition to an index based lookup"""

    infer = "infer"
    none = "none"


class MapErrorEnum(str, Enum):
    """Enum for how to handle key errors in map files"""

    warning = "warning"
    error = "error"


class OutputFormat(str, Enum):
    """
    Output formats
    """

    tsv = "tsv"
    jsonl = "jsonl"
    kgx = "kgx"


class StandardFormat(str, Enum):
    gpi = "gpi"
    bgi = "bgi"
    oban = "oban"


class TransformMode(str, Enum):
    """
    Configures how an external transform file is processed
    flat uses importlib and watches for a StopIteration
    exception, loop runs the code once and expects that
    a for loop is being used to iterate over a file
    """

    flat = "flat"
    loop = "loop"


@dataclass(frozen=True)
class ColumnFilter:
    column: str
    inclusion: FilterInclusion
    filter_code: FilterCode
    value: Union[StrictInt, StrictFloat, StrictStr, List[Union[StrictInt, StrictFloat, StrictStr]]]


@dataclass(frozen=True)
class DatasetDescription:
    """
    These options should be treated as being in alpha, as we need
    to align with various efforts (hcls, translator infores)

    These currently do not serve a purpose in koza other than documentation
    """

    # id: Optional[str] = None          # Can uncomment when we have a standard
    name: Optional[str] = None  # If empty use source name
    ingest_title: Optional[str] = None  # Title of source of data, map to biolink name
    ingest_url: Optional[str] = None  # URL to source of data, maps to biolink iri
    description: Optional[str] = None  # Description of the data/ingest
    # source: Optional[str] = None      # Possibly replaced with provided_by
    provided_by: Optional[str] = None  # <data source>_<type_of_ingest>, ex. hpoa_gene_to_disease
    # license: Optional[str] = None     # Possibly redundant, same as rights
    rights: Optional[str] = None  # License information for the data source


@dataclass(config=PYDANTIC_CONFIG)
class SourceConfig:
    """
    Source config data class

    Parameters
    ----------
    name: str (required) - name of the source
    files: List[str] (required) - list of files to process
    file_archive: str (optional) - path to a file archive containing files to process
    format: FormatType (optional) - format of the data file(s)
    sssom_config: SSSOMConfig (optional) - SSSOM config options
    columns: List[str] (optional) - list of columns to include
    field_type_map: dict (optional) - dict of field names and their type (using the FieldType enum)
    filters: List[ColumnFilter] (optional) - list of filters to apply
    required_properties: List[str] (optional) - list of properties which must be in json data files
    metadata: DatasetDescription (optional) - metadata for the source
    delimiter: str (optional) - delimiter for csv files
    header: int (optional) - header row index (required if format is csv and header is not none)
    header_delimiter: str (optional) - delimiter for header in csv files
    header_prefix: str (optional) - prefix for header in csv files
    comment_char: str (optional) - comment character for csv files
    skip_blank_lines: bool (optional) - skip blank lines in csv files
    json_path: List[str] (optional) - path within JSON object containing data to process
    transform_code: str (optional) - path to a python file to transform the data
    transform_mode: TransformMode (optional) - how to process the transform file
    global_table: str (optional) - path to a global table file
    local_table: str (optional) - path to a local table file
    """

    name: str
    files: List[Union[str, Path]]
    file_archive: Optional[Union[str, Path]] = None
    format: FormatType = FormatType.csv
    sssom_config: Optional[SSSOMConfig] = None
    columns: Optional[List[Union[str, Dict[str, FieldType]]]] = None
    field_type_map: Optional[dict] = None
    filters: List[ColumnFilter] = field(default_factory=list)
    required_properties: Optional[List[str]] = None
    metadata: Optional[Union[DatasetDescription, str]] = None
    delimiter: Optional[str] = None
    header: Union[int, HeaderMode] = HeaderMode.infer
    header_delimiter: Optional[str] = None
    header_prefix: Optional[str] = None
    comment_char: str = "#"
    skip_blank_lines: bool = True
    json_path: Optional[List[Union[StrictStr, StrictInt]]] = None
    transform_code: Optional[str] = None
    transform_mode: TransformMode = TransformMode.flat
    global_table: Optional[Union[str, Dict]] = None
    local_table: Optional[Union[str, Dict]] = None

    def extract_archive(self):
        archive_path = Path(self.file_archive).parent  # .absolute()
        if self.file_archive.endswith(".tar.gz") or self.file_archive.endswith(".tar"):
            with tarfile.open(self.file_archive) as archive:
                archive.extractall(archive_path)
        elif self.file_archive.endswith(".zip"):
            with zipfile.ZipFile(self.file_archive, "r") as archive:
                archive.extractall(archive_path)
        else:
            raise ValueError("Error extracting archive. Supported archive types: .tar.gz, .zip")
        if self.files:
            files = [os.path.join(archive_path, file) for file in self.files]
        else:
            files = [os.path.join(archive_path, file) for file in os.listdir(archive_path)]
        return files

    def __post_init__(self):
        # Get files as paths, or extract them from an archive
        if self.file_archive:
            files = self.extract_archive()
        else:
            files = self.files

        files_as_paths: List[Path] = []
        for file in files:
            if isinstance(file, str):
                files_as_paths.append(Path(file))
            else:
                files_as_paths.append(file)
        object.__setattr__(self, "files", files_as_paths)

        # If metadata looks like a file path attempt to load it from the yaml
        if self.metadata and isinstance(self.metadata, str):
            try:
                with open(self.metadata, "r") as meta:
                    object.__setattr__(self, "metadata", DatasetDescription(**yaml.safe_load(meta)))
            except Exception as e:
                raise ValueError(f"Unable to load metadata from {self.metadata}: {e}")

        # Format tab as delimiter
        if self.delimiter in ["tab", "\\t"]:
            object.__setattr__(self, "delimiter", "\t")

        # Filter columns
        filtered_columns = [column_filter.column for column_filter in self.filters]

        all_columns = []
        if self.columns:
            all_columns = [next(iter(column)) if isinstance(column, Dict) else column for column in self.columns]

        if self.header == HeaderMode.none and not self.columns:
            raise ValueError(
                "there is no header and columns have not been supplied\n"
                "configure the 'columns' field or set header to the 0-based"
                "index in which it appears in the file, or set this value to"
                "'infer'"
            )

        for column in filtered_columns:
            if column not in all_columns:
                raise (ValueError(f"Filter column {column} not in column list"))

        for column_filter in self.filters:
            if column_filter.filter_code in ["lt", "gt", "lte", "gte"]:
                if not isinstance(column_filter.value, (int, float)):
                    raise ValueError(f"Filter value must be int or float for operator {column_filter.filter_code}")
            elif column_filter.filter_code == "eq":
                if not isinstance(column_filter.value, (str, int, float)):
                    raise ValueError(
                        f"Filter value must be string, int or float for operator {column_filter.filter_code}"
                    )
            elif column_filter.filter_code == "in":
                if not isinstance(column_filter.value, List):
                    raise ValueError(f"Filter value must be List for operator {column_filter.filter_code}")

        # Check for conflicting configurations
        if self.format == FormatType.csv and self.required_properties:
            raise ValueError(
                "CSV specified but required properties have been configured\n"
                "Either set format to jsonl or change properties to columns in the config"
            )
        if self.columns and self.format != FormatType.csv:
            raise ValueError(
                "Columns have been configured but format is not csv\n"
                "Either set format to csv or change columns to properties in the config"
            )
        if self.json_path and self.format != FormatType.json:
            raise ValueError(
                "iterate_over has been configured but format is not json\n"
                "Either set format to json or remove iterate_over in the configuration"
            )

        # Create a field_type_map if columns are supplied
        if self.columns:
            field_type_map = {}
            for field in self.columns:
                if isinstance(field, str):
                    field_type_map[field] = FieldType.str
                else:
                    if len(field) != 1:
                        raise ValueError("Field type map contains more than one key")
                    for key, val in field.items():
                        field_type_map[key] = val
            object.__setattr__(self, "field_type_map", field_type_map)


@dataclass(config=PYDANTIC_CONFIG)
class PrimaryFileConfig(SourceConfig):
    """
    Primary configuration for transforming a source file

    Parameters
    ----------
    node_properties: List[str] (optional) - list of node properties/columns to include
    edge_properties: List[str] (optional) - list of edge properties/columns to include
    min_node_count: int (optional) - minimum number of nodes required in output
    min_edge_count: int (optional) - minimum number of edges required in output
    node_report_columns: List[str] (optional) - list of node properties to include in the report
    edge_report_columns: List[str] (optional) - list of edge properties to include in the report
    depends_on: List[str] (optional) - Optional lookup dictionary for basic mapping
    on_map_failure: MapErrorEnum (optional) - How to handle key errors in map files
    """

    node_properties: Optional[List[str]] = None
    edge_properties: Optional[List[str]] = None
    min_node_count: Optional[int] = None
    min_edge_count: Optional[int] = None
    # node_report_columns: Optional[List[str]] = None
    # edge_report_columns: Optional[List[str]] = None
    depends_on: List[str] = field(default_factory=list)
    on_map_failure: MapErrorEnum = MapErrorEnum.warning


@dataclass(config=PYDANTIC_CONFIG)
class MapFileConfig(SourceConfig):
    key: Optional[str] = None
    values: Optional[List[str]] = None
    curie_prefix: Optional[str] = None
    add_curie_prefix_to_columns: Optional[List[str]] = None
    depends_on: Optional[List[str]] = None
