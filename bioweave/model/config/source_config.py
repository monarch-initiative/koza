"""
source config data class
map config data class
"""
from typing import Union, List, Dict
from pydantic.dataclasses import dataclass
from pathlib import Path
from enum import Enum


class MapErrorEnum(str, Enum):
    """
    Enum for how to handle key errors
    in map files
    """
    warning = 'warning'
    error = 'error'


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

    delimiter:
    separator string similar to what works in str.split()
    https://docs.python.org/3/library/stdtypes.html#str.split
    """

    name: str
    file_metadata: DatasetDescription
    depends_on: List[str]
    files: List[Union[str, Path]]
    fields: List[Union[str, Dict[str, str]]]
    format: str = 'tsv'
    delimiter: str = None
    header_delimiter: str = None
    skip_lines: int = 0
    compression: CompressionType = None
    filter_in: List[Dict[str, Filter]] = None
    filter_out: List[Dict[str, Filter]] = None

    def __post_init__(self):
        files_as_paths: List[Path] = []
        for file in self.files:
            if isinstance(file, str):
                files_as_paths.append(Path(file))
            else:
                files_as_paths.append(file)
        object.__setattr__(self, 'files', files_as_paths)

        # some basic type checking? if lt, gt, lte, gte
        # make sure that filter is int or float?

        # enum for accepted types?

        # do we parse the field-type map here, private attr?


@dataclass(frozen=True)
class PrimarySourceConfig(SourceConfig):
    associations: List[str] = None
    field_mappings: Dict[str, str] = None
    depends_on: List[str] = None
    on_map_failure: MapErrorEnum = MapErrorEnum.warning


@dataclass(frozen=True)
class MapSourceConfig(SourceConfig):
    key: str = None
    values: List[str] = None
