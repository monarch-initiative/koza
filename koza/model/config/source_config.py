"""
source config data class
map config data class
"""
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Union

from glom import Path as GlomPath
from pydantic import StrictFloat, StrictInt, StrictStr
from pydantic.dataclasses import dataclass
from pydantic.tools import parse_obj_as


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


@dataclass(frozen=True)
class ColumnFilter:
    column: str
    inclusion: FilterInclusion
    filter_code: FilterCode
    value: Union[StrictInt, StrictFloat, StrictStr, List[Union[StrictInt, StrictFloat, StrictStr]]]


@dataclass(frozen=True)
class DatasetDescription:
    ingest_title: str = None
    ingest_url: str = None
    license_url: str = None
    data_rights: str = None


@dataclass(frozen=True)
class SourceMetadata:
    name: str
    data_dir: Union[str, Path]
    dataset_description: DatasetDescription
    source_templates: List[str]
    map_templates: List[str]

    def __post_init__(self):
        if isinstance(self.data_dir, str):
            object.__setattr__(self, 'data_dir', Path(self.data_dir))


@dataclass(frozen=True)
class SourceConfig:
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
    file_metadata: DatasetDescription
    files: List[Union[str, Path]]
    format: FormatType = FormatType.csv
    columns: List[Union[str, Dict[str, FieldType]]] = None
    required_properties: List[str] = None
    delimiter: str = None
    header_delimiter: str = None
    skip_lines: int = 0
    skip_blank_lines: bool = True
    compression: CompressionType = None
    filters: List[ColumnFilter] = None
    glom_path: List[Any] = None

    def __post_init__(self):
        files_as_paths: List[Path] = []
        for file in self.files:
            if isinstance(file, str):
                files_as_paths.append(Path(file))
            else:
                files_as_paths.append(file)
        object.__setattr__(self, 'files', files_as_paths)

        column_filters = parse_obj_as(List[ColumnFilter], self.filters)
        filtered_columns = [column_filter.column for column_filter in column_filters]

        all_columns = [next(iter(column)) if isinstance(column, Dict) else column for column in self.columns]

        for column in filtered_columns:
            if column not in all_columns:
                raise(
                    ValueError(
                        f"Filter column {column} not in column list"
                    )
                )

        if self.delimiter in ['tab', '\\t']:
            object.__setattr__(self, 'delimiter', '\t')

        for column_filter in column_filters:
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
                f"csv specified but required properties have been configured\n"
                f"either set format to jsonl or change properties to columns in the config"
            )

        if self.columns and self.format != FormatType.csv:
            raise ValueError(
                f"columns have been configured but format is not csv\n"
                f"either set format to csv or change columns to properties in the config"
            )

        if self.glom_path and self.format != FormatType.json:
            raise ValueError(
                f"iterate_over has been configured but format is not json\n"
                f"either set format to json or remove iterate_over in the configuration"
            )

        if self.columns:
            pass
        # do we parse the field-type map here, private attr?

        if self.glom_path:
            object.__setattr__(self, 'glom_path', GlomPath(*self.glom_path))


@dataclass(frozen=True)
class PrimarySourceConfig(SourceConfig):
    depends_on: List[str] = None  # field(default_factory=list)
    on_map_failure: MapErrorEnum = MapErrorEnum.warning


@dataclass(frozen=True)
class MapSourceConfig(SourceConfig):
    key: str = None
    values: List[str] = None
