"""
source config data class
map config data class
"""
from enum import Enum
from pathlib import Path
from typing import Dict, List, Union

from pydantic import StrictFloat, StrictInt, StrictStr
from pydantic.dataclasses import dataclass

from koza.model.config.pydantic_config import PydanticConfig


class MapErrorEnum(str, Enum):
    """
    Enum for how to handle key errors in map files
    """

    warning = 'warning'
    error = 'error'


class FormatType(str, Enum):
    """
    Enum for supported file types
    """

    csv = 'csv'
    jsonl = 'jsonl'
    json = 'json'


class StandardFormat(str, Enum):
    gpi = 'gpi'
    bgi = 'bgi'
    oban = 'oban'


class CompressionType(str, Enum):
    """
    Enum for supported compression
    """

    gzip = 'gzip'
    none = 'none'


class FilterCode(str, Enum):
    """
    Enum for filter codes
    eg gt (greater than)
    """

    gt = 'gt'
    ge = 'ge'
    lt = 'lt'
    lte = 'le'
    eq = 'eq'
    ne = 'ne'
    inlist = 'in'


class FilterInclusion(str, Enum):
    """
    Enum for filter inclusion/exclusion
    """

    include = 'include'
    exclude = 'exclude'


class FieldType(str, Enum):
    """
    Enum for filter codes
    eg gt (greater than)
    """

    str = 'str'
    int = 'int'
    float = 'float'
    # Proportion = 'Proportion'


class OutputFormat(str, Enum):
    """
    Have this set up but for prototyping removing this
    as an option to only support the TSV output format
    """

    tsv = 'tsv'
    json = 'json'
    jsonl = 'jsonl'


class TransformMode(str, Enum):
    """
    Have this set up but for prototyping removing this
    as an option to only support the TSV output format
    """

    flat = 'flat'
    loop = 'loop'


@dataclass(frozen=True)
class ColumnFilter:
    column: str
    inclusion: FilterInclusion
    filter_code: FilterCode
    value: Union[StrictInt, StrictFloat, StrictStr, List[Union[StrictInt, StrictFloat, StrictStr]]]


@dataclass(frozen=True)
class DatasetDescription:
    id: str = None  # TODO constrain to a curie?
    name: str = None  # If empty use source name
    ingest_title: str = None  # Map to biolink name
    ingest_url: str = None  # Maps to biolink iri
    description: str = None
    source: str = None
    provided_by: str = None
    license: str = None
    rights: str = None


@dataclass(config=PydanticConfig)
class SourceConfig:
    source_files: List[str]
    name: str = None
    output_format: OutputFormat = None
    dataset_description: DatasetDescription = None


@dataclass(config=PydanticConfig)
class SourceFileConfig:
    """
    Base class for primary sources and mapping sources

    TODO document fields

    TODO override translation table path?

    delimiter:
    separator string similar to what works in str.split()
    https://docs.python.org/3/library/stdtypes.html#str.split

    required_properties: A list of required top level properties in a json object
    """

    name: str
    files: List[Union[str, Path]]
    format: FormatType = FormatType.csv
    path: Path = None
    standard_format: StandardFormat = None
    file_metadata: DatasetDescription = None
    columns: List[Union[str, Dict[str, FieldType]]] = None
    node_properties: List[str] = None
    edge_properties: List[str] = None
    required_properties: List[str] = None
    delimiter: str = None
    header_delimiter: str = None
    has_header: bool = True
    skip_lines: int = 0
    skip_blank_lines: bool = True
    compression: CompressionType = None
    filters: List[ColumnFilter] = None
    json_path: List[Union[StrictStr, StrictInt]] = None
    transform_code: str = None
    transform_mode: TransformMode = TransformMode.flat

    def __post_init_post_parse__(self):
        files_as_paths: List[Path] = []
        for file in self.files:
            if isinstance(file, str):
                files_as_paths.append(Path(file))
            else:
                files_as_paths.append(file)
        object.__setattr__(self, 'files', files_as_paths)

        # todo: where should this really be stored? defaults for a format should probably be defined in yaml
        if self.standard_format == StandardFormat.gpi:
            self.format = FormatType.csv
            self.delimiter = "\t"
            self.columns = [
                "DB",
                "DB_Object_ID",
                "DB_Object_Symbol",
                "DB_Object_Name",
                "DB_Object_Synonym(s)",
                "DB_Object_Type",
                "Taxon",
                "Parent_Object_ID",
                "DB_Xref(s)",
                "Properties",
            ]
        elif self.standard_format == StandardFormat.oban:
            self.format = FormatType.csv
            self.delimiter = ","
            self.columns = [
                "SUBJECT",
                "SUBJECT_LABEL",
                "SUBJECT_TAXON",
                "SUBJECT_TAXON_LABEL",
                "OBJECT",
                "OBJECT_LABEL",
                "RELATION",
                "RELATION_LABEL",
                "EVIDENCE",
                "EVIDENCE_LABEL",
                "SOURCE",
                "IS_DEFINED_BY",
                "QUALIFIER",
            ]

        if self.delimiter in ['tab', '\\t']:
            object.__setattr__(self, 'delimiter', '\t')

        if self.filters is None:
            self.filters = []

        filtered_columns = [column_filter.column for column_filter in self.filters]

        all_columns = []
        if self.columns:
            all_columns = [
                next(iter(column)) if isinstance(column, Dict) else column
                for column in self.columns
            ]

        for column in filtered_columns:
            if column not in all_columns:
                raise (ValueError(f"Filter column {column} not in column list"))

        for column_filter in self.filters:
            if column_filter.filter_code in ['lt', 'gt', 'lte', 'gte']:
                # TODO determine if this should raise an exception
                # or instead try to type coerce the string to a float
                # type coercion is probably the best thing to do here
                if not isinstance(column_filter.value, (int, float)):
                    raise ValueError(
                        f"Filter value must be int or float for operator {column_filter.filter_code}"
                    )
            elif column_filter.filter_code == 'eq':
                if not isinstance(column_filter.value, (str, int, float)):
                    raise ValueError(
                        f"Filter value must be string, int or float for operator {column_filter.filter_code}"
                    )
            elif column_filter.filter_code == 'in':
                if not isinstance(column_filter.value, List):
                    raise ValueError(
                        f"Filter value must be List for operator {column_filter.filter_code}"
                    )

        if self.format == FormatType.csv and self.required_properties:
            raise ValueError(
                "csv specified but required properties have been configured\n"
                "either set format to jsonl or change properties to columns in the config"
            )

        if self.columns and self.format != FormatType.csv:
            raise ValueError(
                "columns have been configured but format is not csv\n"
                "either set format to csv or change columns to properties in the config"
            )

        if self.json_path and self.format != FormatType.json:
            raise ValueError(
                "iterate_over has been configured but format is not json\n"
                "either set format to json or remove iterate_over in the configuration"
            )

        if self.columns:
            _field_type_map = {}
            for field in self.columns:
                if isinstance(field, str):
                    _field_type_map[field] = FieldType.str
                else:
                    if len(field) != 1:
                        # TODO expand this exception msg
                        raise ValueError("Field type map contains more than one key")
                    for key, val in field.items():
                        _field_type_map[key] = val
            object.__setattr__(self, '_field_type_map', _field_type_map)

    @property
    def field_type_map(self):
        return self._field_type_map


@dataclass(config=PydanticConfig)
class PrimaryFileConfig(SourceFileConfig):
    depends_on: List[str] = None  # field(default_factory=list)
    on_map_failure: MapErrorEnum = MapErrorEnum.warning


@dataclass(config=PydanticConfig)
class MapFileConfig(SourceFileConfig):
    source: str = None
    key: str = None
    values: List[str] = None
    curie_prefix: str = None
    add_curie_prefix_to_columns: List[str] = None
