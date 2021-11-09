"""
source config data class
map config data class
"""
import logging
from dataclasses import field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Union

import yaml
from pydantic import StrictFloat, StrictInt, StrictStr
from pydantic.dataclasses import dataclass

from koza.model.config.pydantic_config import PydanticConfig

LOG = logging.getLogger(__name__)


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
    yaml = 'yaml'
    xml = 'xml'  # TODO


class StandardFormat(str, Enum):
    gpi = 'gpi'
    bgi = 'bgi'
    oban = 'oban'


class CompressionType(str, Enum):
    """
    Enum for supported compression
    """

    gzip = 'gzip'


class FilterCode(str, Enum):
    """
    Enum for filter codes
    eg gt (greater than)

    This should be aligned with https://docs.python.org/3/library/operator.html
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


class OutputFormat(str, Enum):
    """
    Output formats
    """

    tsv = 'tsv'
    jsonl = 'jsonl'
    kgx = 'kgx'


class TransformMode(str, Enum):
    """
    Configures how an external transform file is processed
    flat uses importlib and watches for a StopIteration
    exception, loop runs the code once and expects that
    a for loop is being used to iterate over a file
    """

    flat = 'flat'
    loop = 'loop'


class HeaderMode(str, Enum):
    """
    Enum for supported header modes in addition to an index based lookup
    """

    infer = 'infer'
    none = 'none'


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

    These currently do not serve a purpose in koza other
    than documentation
    """

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
    """
    Base class for primary sources and mapping sources

    TODO document fields

    header: Optional, int|HeaderMode - the index (0 based) in which the
            header appears in the file.  If header is set to infer
            the headers will be set to the first line that is not blank
            or commented with a hash.  If header is set to 'none'
            then the columns field will be used, or raise a ValueError
            if columns are not supplied

    delimiter:
    separator string similar to what works in str.split()
    https://docs.python.org/3/library/stdtypes.html#str.split

    required_properties: A list of required top level properties in a json object
    """

    name: str
    files: List[Union[str, Path]]
    format: FormatType = FormatType.csv
    metadata: Union[DatasetDescription, str] = None
    columns: List[Union[str, Dict[str, FieldType]]] = None
    required_properties: List[str] = None
    delimiter: str = None
    header_delimiter: str = None
    header: Union[int, HeaderMode] = HeaderMode.infer
    comment_char: str = '#'
    skip_blank_lines: bool = True
    compression: CompressionType = None
    filters: List[ColumnFilter] = field(default_factory=list)
    json_path: List[Union[StrictStr, StrictInt]] = None
    transform_code: str = None
    transform_mode: TransformMode = TransformMode.flat
    global_table: Union[str, Dict] = None
    local_table: Union[str, Dict] = None


    def __post_init_post_parse__(self):
        """
        TO DO figure out why we're using object.__setattr__(self, ...
              here and document it
        """
        files_as_paths: List[Path] = []
        for file in self.files:
            if isinstance(file, str):
                files_as_paths.append(Path(file))
            else:
                files_as_paths.append(file)
        object.__setattr__(self, 'files', files_as_paths)

        if self.metadata and isinstance(self.metadata, str):
            # If this looks like a file path attempt to load it from the yaml
            # TODO enforce that this is imported via an include?
            # See https://github.com/monarch-initiative/koza/issues/46
            try:
                object.__setattr__(
                    self, 'metadata', DatasetDescription(**yaml.safe_load(self.metadata))
                )
            except Exception:
                # TODO check for more explicit exceptions
                LOG.warning("Could not load dataset description from metadata file")

        if self.delimiter in ['tab', '\\t']:
            object.__setattr__(self, 'delimiter', '\t')

        filtered_columns = [column_filter.column for column_filter in self.filters]

        all_columns = []
        if self.columns:
            all_columns = [
                next(iter(column)) if isinstance(column, Dict) else column
                for column in self.columns
            ]

        if self.header == HeaderMode.none and not self.columns:
            raise ValueError(
                f"there is no header and columns have not been supplied\n"
                f"configure the 'columns' field or set header to the 0-based"
                "index in which it appears in the file, or set this value to"
                "'infer'"
            )

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
class PrimaryFileConfig(SourceConfig):
    """
    node_properties and edge_properties are used for configuring
    the KGX writer
    """

    node_properties: List[str] = None
    edge_properties: List[str] = None
    depends_on: List[str] = field(default_factory=list)
    on_map_failure: MapErrorEnum = MapErrorEnum.warning


@dataclass(config=PydanticConfig)
class MapFileConfig(SourceConfig):
    key: str = None
    values: List[str] = None
    curie_prefix: str = None
    add_curie_prefix_to_columns: List[str] = None
