"""
source config data class
map config data class
"""

from dataclasses import field, fields
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

import yaml
from ordered_set import OrderedSet
from pydantic import (Discriminator, Field, StrictFloat, StrictInt, StrictStr,
                      Tag, TypeAdapter, model_validator)
from pydantic.dataclasses import dataclass
from pydantic_core import ArgsKwargs

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
    passthrough = "passthrough"


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


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class BaseColumnFilter:
    column: str
    inclusion: FilterInclusion


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class ComparisonFilter(BaseColumnFilter):
    filter_code: Literal[FilterCode.lt, FilterCode.gt, FilterCode.lte, FilterCode.ge]
    value: Union[StrictInt, StrictFloat]


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class EqualsFilter(BaseColumnFilter):
    filter_code: Literal[FilterCode.eq]
    value: Union[StrictInt, StrictFloat, StrictStr]


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class NotEqualsFilter(BaseColumnFilter):
    filter_code: Literal[FilterCode.ne]
    value: Union[StrictInt, StrictFloat, StrictStr]


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class InListFilter(BaseColumnFilter):
    filter_code: Literal[FilterCode.inlist, FilterCode.inlist_exact]
    value: List[Union[StrictInt, StrictFloat, StrictStr]]


ColumnFilter = Annotated[
    Union[ComparisonFilter, EqualsFilter, NotEqualsFilter, InListFilter],
    Field(..., discriminator="filter_code"),
]


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


# Reader configuration
# ---


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class BaseReaderConfig:
    files: List[str] = field(default_factory=list)


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class CSVReaderConfig(BaseReaderConfig):
    format: Literal[FormatType.csv] = FormatType.csv
    columns: Optional[List[Union[str, Dict[str, FieldType]]]] = None
    field_type_map: Optional[dict[str, FieldType]] = None
    delimiter: str = "\t"
    header_delimiter: Optional[str] = None
    dialect: str = "excel"
    header_mode: Union[int, HeaderMode] = HeaderMode.infer
    header_delimiter: Optional[str] = None
    header_prefix: Optional[str] = None
    skip_blank_lines: bool = True
    comment_char: str = "#"

    def __post_init__(self):
        # Format tab as delimiter
        if self.delimiter in ["tab", "\\t"]:
            object.__setattr__(self, "delimiter", "\t")

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

        if self.header_mode == HeaderMode.none and not self.columns:
            raise ValueError(
                "there is no header and columns have not been supplied\n"
                "configure the 'columns' field or set header to the 0-based"
                "index in which it appears in the file, or set this value to"
                "'infer'"
            )


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class JSONLReaderConfig(BaseReaderConfig):
    format: Literal[FormatType.jsonl] = FormatType.jsonl
    required_properties: Optional[List[str]] = None


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class JSONReaderConfig(BaseReaderConfig):
    format: Literal[FormatType.json] = FormatType.json
    required_properties: Optional[List[str]] = None
    json_path: Optional[List[Union[StrictStr, StrictInt]]] = None


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class YAMLReaderConfig(BaseReaderConfig):
    format: Literal[FormatType.yaml] = FormatType.yaml
    required_properties: Optional[List[str]] = None
    json_path: Optional[List[Union[StrictStr, StrictInt]]] = None


def get_reader_discriminator(model: Any):
    if isinstance(model, dict):
        return model.get("format", FormatType.csv)
    return getattr(model, "format", FormatType.csv)


ReaderConfig = Annotated[
    (
        Annotated[CSVReaderConfig, Tag(FormatType.csv)]
        | Annotated[JSONLReaderConfig, Tag(FormatType.jsonl)]
        | Annotated[JSONReaderConfig, Tag(FormatType.json)]
        | Annotated[YAMLReaderConfig, Tag(FormatType.yaml)]
    ),
    Discriminator(get_reader_discriminator),
]


# Transform configuration
# ---


@dataclass(config=PYDANTIC_CONFIG, frozen=True, kw_only=True)
class TransformConfig:
    """
    Source config data class

    Parameters
    ----------
    name: name of the source
    code: path to a python file to transform the data
    mode: how to process the transform file
    global_table: path to a global table file
    local_table: path to a local table file
    """

    code: Optional[str] = None
    module: Optional[str] = None
    filters: List[ColumnFilter] = field(default_factory=list)
    global_table: Optional[Union[str, Dict]] = None
    local_table: Optional[Union[str, Dict]] = None
    mappings: List[str] = field(default_factory=list)
    on_map_failure: MapErrorEnum = MapErrorEnum.warning
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def extract_extra_fields(cls, values: dict | ArgsKwargs) -> Dict[str, Any]:
        """Take any additional kwargs and put them in the `extra_fields` attribute."""
        if isinstance(values, dict):
            kwargs = values.copy()
        elif isinstance(values, ArgsKwargs) and values.kwargs is not None:
            kwargs = values.kwargs.copy()
        else:
            kwargs = {}

        configured_field_names = {f.name for f in fields(cls) if f.name != "extra_fields"}
        extra_fields: dict[str, Any] = kwargs.pop("extra_fields", {})

        for field_name in list(kwargs.keys()):
            if field_name in configured_field_names:
                continue
            extra_fields[field_name] = kwargs.pop(field_name)
        kwargs["extra_fields"] = extra_fields

        return kwargs


# Writer configuration
# ---


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class WriterConfig:
    format: OutputFormat = OutputFormat.tsv
    sssom_config: Optional[SSSOMConfig] = None
    node_properties: Optional[List[str]] = None
    edge_properties: Optional[List[str]] = None
    min_node_count: Optional[int] = None
    min_edge_count: Optional[int] = None


# Main Koza configuration
# ---


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class KozaConfig:
    name: str
    reader: ReaderConfig = field(default_factory=CSVReaderConfig)
    transform: TransformConfig = field(default_factory=TransformConfig)
    writer: WriterConfig = field(default_factory=WriterConfig)
    metadata: Optional[Union[DatasetDescription, str]] = None

    def __post_init__(self):
        # If metadata looks like a file path attempt to load it from the yaml
        if self.metadata and isinstance(self.metadata, str):
            try:
                with open(self.metadata, "r") as meta:
                    object.__setattr__(self, "metadata", DatasetDescription(**yaml.safe_load(meta)))
            except Exception as e:
                raise ValueError(f"Unable to load metadata from {self.metadata}: {e}") from e

        if self.reader.format == FormatType.csv and self.reader.columns is not None:
            filtered_columns = OrderedSet([column_filter.column for column_filter in self.transform.filters])
            all_columns = OrderedSet([
                column if isinstance(column, str) else list(column.keys())[0] for column in self.reader.columns
            ])
            extra_filtered_columns = filtered_columns - all_columns
            if extra_filtered_columns:
                quote = "'"
                raise ValueError(
                    "One or more filter columns not present in designated CSV columns:"
                    f" {', '.join([f'{quote}{c}{quote}' for c in extra_filtered_columns])}"
                )


def SourceConfig(**kwargs):
    return DEPRECATEDSourceConfig(**kwargs).to_new_transform()


@dataclass(config=PYDANTIC_CONFIG)
class DEPRECATEDSourceConfig:
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

    metadata: Optional[Union[DatasetDescription, str]] = None

    node_properties: Optional[List[str]] = None
    edge_properties: Optional[List[str]] = None
    min_node_count: Optional[int] = None
    min_edge_count: Optional[int] = None
    # node_report_columns: Optional[List[str]] = None
    # edge_report_columns: Optional[List[str]] = None
    depends_on: List[str] = field(default_factory=list)
    on_map_failure: MapErrorEnum = MapErrorEnum.warning

    def to_new_transform(self):
        files = self.files or []
        if self.file_archive:
            files.append(self.file_archive)

        config_obj = {
            "name": self.name,
            "metadata": self.metadata,
            "reader": {
                "format": self.format,
                "files": files,
                "columns": self.columns,
                "field_type_map": self.field_type_map,
                "required_properties": self.required_properties,
                "delimiter": self.delimiter,
                "header_mode": self.header,  # Renamed to header_mode
                "header_delimiter": self.header_delimiter,
                "header_prefix": self.header_prefix,
                "comment_char": self.comment_char,
                "skip_blank_lines": self.skip_blank_lines,
                "json_path": self.json_path,
            },
            "transform": {
                "code": self.transform_code,
                "filters": self.filters,
                "mapping": self.depends_on,
                "global_table": self.global_table,
                "local_table": self.local_table,
            },
            "writer": {
                "format": self.format,
                "sssom_config": self.sssom_config,
                "node_properties": self.node_properties,
                "edge_properties": self.edge_properties,
                "min_node_count": self.min_node_count,
                "min_edge_count": self.min_edge_count,
            },
        }

        return TypeAdapter(KozaConfig).validate_python(config_obj)
