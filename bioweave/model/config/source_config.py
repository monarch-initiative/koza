"""
source config data class
map config data class
"""
from typing import Union, List, Dict
from pydantic.dataclasses import dataclass
from pydantic import ValidationError
from dataclasses import field
from pathlib import Path
from enum import Enum


class MapErrorEnum(str, Enum):
    """
    Enum for how to handle key errors
    in map files
    """
    warning = 'warning'
    error = 'error'


class FormatType(str, Enum):
    """
    Enum for supported compression
    """
    tsv = 'tsv'
    csv = 'csv'
    jsonl = 'jsonl'


class CompressionType(str, Enum):
    """
    Enum for supported compression
    """
    gzip = 'gzip'


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
    format: FormatType = 'tsv'
    columns: List[Union[str, Dict[str, str]]] = None
    properties: List[Dict[str, str]] = None
    depends_on: List[str] = field(default_factory=list)
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

        # some basic type checking? if lt, gt, lte, gte
        # make sure that filter is int or float?

        for flter in all_filters:
            if flter['filter'] in ['lt', 'gt', 'lte', 'gte']:
                if not isinstance(flter['value'], (int, float)):
                    raise ValueError(
                        f"Filter value must be int or float for operator {flter['filter']}"
                    )

        # enum for accepted types?

        # do we parse the field-type map here, private attr?


@dataclass(frozen=True)
class PrimarySourceConfig(SourceConfig):
    depends_on: List[str] = None
    on_map_failure: MapErrorEnum = MapErrorEnum.warning


@dataclass(frozen=True)
class MapSourceConfig(SourceConfig):
    key: str = None
    values: List[str] = None
