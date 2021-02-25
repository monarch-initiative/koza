"""
source config data class
map config data class
"""
from dataclasses import field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Union

from pydantic.dataclasses import dataclass


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
    gte = 'gte'
    lt = 'lt'
    lte = 'lte'
    eq = 'eq'
    ne = 'ne'


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
class Filter:
    filter: FilterCode
    value: Union[str, int, float]


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
    """

    name: str
    file_metadata: DatasetDescription
    files: List[Union[str, Path]]
    format: FormatType = FormatType.csv
    columns: List[Union[str, Dict[str, FieldType]]] = None
    properties: List[str] = None
    delimiter: str = None
    header_delimiter: str = None
    skip_lines: int = 0
    compression: CompressionType = None
    filter_in: List[Dict[str, Filter]] = field(default_factory=list)
    filter_out: List[Dict[str, Filter]] = field(default_factory=list)

    def __post_init__(self):
        files_as_paths: List[Path] = []
        for file in self.files:
            if isinstance(file, str):
                files_as_paths.append(Path(file))
            else:
                files_as_paths.append(file)
        object.__setattr__(self, 'files', files_as_paths)

        all_filters = [filters for f_in in self.filter_in for filters in f_in.values()]
        all_filters += [filters for f_out in self.filter_out for filters in f_out.values()]

        if self.delimiter in ['tab', '\\t']:
            object.__setattr__(self, 'delimiter', '\t')

        for flter in all_filters:
            if flter['filter'] in ['lt', 'gt', 'lte', 'gte']:
                # TODO determine if this should raise an exception
                # or instead try to type coerce the string to a float
                if not isinstance(flter['value'], (int, float)):
                    raise ValueError(
                        f"Filter value must be int or float for operator {flter['filter']}"
                    )

        if format is FormatType.csv and self.properties:
            raise ValueError(
                f"csv specified but properties have been configured\n"
                f"either set format to jsonl or change properties to columns in the config"
            )

        if format is FormatType.jsonl and self.columns:
            raise ValueError(
                f"jsonl specified but columns have been configured\n"
                f"either set format to csv or change columns to properties in the config"
            )
        if self.columns:
            pass
        # do we parse the field-type map here, private attr?


@dataclass(frozen=True)
class PrimarySourceConfig(SourceConfig):
    depends_on: List[str] = None  # field(default_factory=list)
    on_map_failure: MapErrorEnum = MapErrorEnum.warning


@dataclass(frozen=True)
class MapSourceConfig(SourceConfig):
    key: str = None
    values: List[str] = None
