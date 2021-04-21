from dataclasses import dataclass
from typing import Any, Dict, Iterator, List

from koza.io.reader.csv_reader import CSVReader
from koza.io.reader.json_reader import JSONReader
from koza.io.reader.jsonl_reader import JSONLReader
from koza.io.utils import open_file, open_resource
from koza.model.config.source_config import DatasetDescription, SourceFileConfig
from koza.model.translation_table import TranslationTable
from koza.row_filter import RowFilter


@dataclass
class Source:
    """
    For simplicity copying over all the fields
    from source_config.SourceConfig

    avoids nesting but also a DRY violation?
    """

    source_files: List[str]
    name: str = None
    dataset_description: DatasetDescription = None
    translation_table: TranslationTable = None


class SourceFile:
    """
    An iterator that provides a layer of abstraction over file types
    and adds filter support to the readers in io.reader

    config: Source config
    reader: An iterator that takes in an IO[str] as its first argument
    and yields a dictionary
    """

    def __init__(self, config: SourceFileConfig):

        self.config = config
        self._filter = RowFilter(config.filters)

        for file in config.files:
            resource_io = open_file(file, config.compression)
            if self.config.format == 'csv':
                self._reader = CSVReader(
                    resource_io,
                    name=config.name,
                    field_type_map=config.field_type_map,
                    delimiter=config.delimiter,
                    header_delimiter=config.header_delimiter,
                    skip_lines=config.skip_lines,
                )
            elif self.config.format == 'jsonl':
                self._reader = JSONLReader(
                    resource_io,
                    name=config.name,
                    required_properties=config.required_properties,
                )
            elif self.config.format == 'json':
                self._reader = JSONReader(
                    resource_io,
                    name=config.name,
                    required_properties=config.required_properties,
                )
            else:
                raise ValueError(f"File type {format} not supported")

    def __iter__(self) -> Iterator:
        return self

    def __next__(self) -> Dict[str, Any]:
        if self._filter:
            row = next(self._reader)
            while not self._filter.include_row(row):
                # TODO log filtered out lines
                row = next(self._reader)

            return row
        else:
            row = next(self._reader)
        return row
