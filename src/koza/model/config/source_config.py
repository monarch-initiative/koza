"""
source config data class
map config data class
"""

from dataclasses import field
from enum import Enum
from pathlib import Path

from pydantic import StrictInt, StrictStr, TypeAdapter
from pydantic.dataclasses import dataclass

from koza.model.config.pydantic_config import PYDANTIC_CONFIG
from koza.model.config.sssom_config import SSSOMConfig
from koza.model.filters import ColumnFilter
from koza.model.formats import InputFormat
from koza.model.koza import DatasetDescription, KozaConfig
from koza.model.reader import FieldType, HeaderMode
from koza.model.transform import MapErrorEnum


class TransformMode(str, Enum):
    """
    Configures how an external transform file is processed
    flat uses importlib and watches for a StopIteration
    exception, loop runs the code once and expects that
    a for loop is being used to iterate over a file
    """

    flat = "flat"
    loop = "loop"


def SourceConfig(**kwargs):
    return _DeprecatedSourceConfig(**kwargs).to_new_transform()


@dataclass(config=PYDANTIC_CONFIG)
class _DeprecatedSourceConfig:
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
    max_edge_count: int (optional) - minimum number of edges required to write output
    max_node_count: int (optional) - minimum number of nodes required to write output
    """

    name: str
    files: list[str | Path]
    file_archive: str | Path | None = None
    format: InputFormat = InputFormat.csv
    sssom_config: SSSOMConfig | None = None
    columns: list[str | dict[str, FieldType]] | None = None
    field_type_map: dict | None = None
    filters: list[ColumnFilter] = field(default_factory=list)
    required_properties: list[str] | None = None
    metadata: DatasetDescription | str | None = None
    delimiter: str | None = None
    header: int | HeaderMode = HeaderMode.infer
    header_delimiter: str | None = None
    header_prefix: str | None = None
    comment_char: str = "#"
    skip_blank_lines: bool = True
    json_path: list[StrictStr | StrictInt] | None = None
    transform_code: str | None = None
    transform_mode: TransformMode = TransformMode.flat
    global_table: str | dict | None = None
    local_table: str | dict | None = None

    metadata: DatasetDescription | str | None = None

    node_properties: list[str] | None = None
    edge_properties: list[str] | None = None
    min_node_count: int | None = None
    min_edge_count: int | None = None
    max_node_count: int | None = None
    max_edge_count: int | None = None
    # node_report_columns: Optional[List[str]] = None
    # edge_report_columns: Optional[List[str]] = None
    depends_on: list[str] = field(default_factory=list)
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
                "max_node_count": self.max_node_count,
                "max_edge_count": self.max_edge_count,
            }
        }

        return TypeAdapter(KozaConfig).validate_python(config_obj)
