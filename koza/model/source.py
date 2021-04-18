from dataclasses import dataclass
from typing import Any, Dict, Iterator, List

from koza.io.reader.csv_reader import CSVReader
from koza.io.reader.json_reader import JSONReader
from koza.io.reader.jsonl_reader import JSONLReader
from koza.io.utils import open_resource
from koza.model.config.source_config import DatasetDescription, OutputFormat, SourceFileConfig
from koza.model.translation_table import TranslationTable
from koza.row_filter import RowFilter


@dataclass
class Source:
    """
    For simplicity copying over all the fields
    from source_config.SourceConfig

    avoids nesting but also a DRY violation?
    """

    name: str
    data_dir: str
    output_dir: str
    source_files: List[str]
    output_format: OutputFormat = None
    map_files: List[str] = None
    dataset_description: DatasetDescription = None
    translation_table: TranslationTable = None


@dataclass
class SourceFile:
    """
    An iterator that provides a layer of abstraction over file types
    and adds filter support to the readers in io.reader

    config: Source config
    reader: An iterator that takes in an IO[str] as its first argument
    and yields a dictionary
    """

    config: SourceFileConfig
    filter: RowFilter
    _reader: Iterator[Dict[str, Any]]

    def __init__(self, config: SourceFileConfig, filter: RowFilter = None):

        for file in config.files:
            with open_resource(file, config.compression) as resource_io:
                if format == 'csv':
                    self._reader = CSVReader(
                        resource_io,
                        name=config.name,
                        field_type_map=config.field_type_map,
                        delimiter=config.delimiter,
                        header_delimiter=config.header_delimiter,
                        skip_lines=config.skip_lines,
                    )
                elif format == 'jsonl':
                    self._reader = JSONLReader(
                        resource_io,
                        name=config.name,
                        required_properties=config.required_properties,
                    )
                elif format == 'json':
                    self._reader = JSONReader(
                        resource_io,
                        name=config.name,
                        required_properties=config.required_properties,
                    )
                else:
                    raise ValueError

    def __iter__(self) -> Iterator:
        return self

    def __next__(self) -> Dict[str, Any]:
        if self.filter:
            row = next(self._reader)
            while not self.filter.include_row(row):
                # TODO log filtered out lines
                row = next(self._reader)

            return row
        else:
            row = next(self._reader)
        return row
