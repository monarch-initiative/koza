from typing import Any, Dict, Iterator, List, Optional, Union

import yaml

from koza.io.reader.csv_reader import CSVReader
from koza.io.reader.json_reader import JSONReader
from koza.io.reader.jsonl_reader import JSONLReader
from koza.io.utils import open_resource
from koza.io.yaml_loader import UniqueIncludeLoader
from koza.model.config.source_config import MapFileConfig, PrimaryFileConfig, SourceConfig
from koza.row_filter import RowFilter


class Source:
    """
    Source class for files and maps

    Source is an iterator that provides a layer of abstraction over file types
    and adds filter support to the readers in io.reader

    config: Source config
    reader: An iterator that takes in an IO[str] as its first argument
    and yields a dictionary
    """

    def __init__(
        self,
        config: Union[PrimaryFileConfig, MapFileConfig, str],
        row_limit: Optional[int] = None
    ):

        self.config = config
        self.row_limit = row_limit
        self._filter = RowFilter(config.filters)
        self._reader = None
        self._readers: List = []
        self.last_row: Optional[Dict] = None


        if not isinstance(config, SourceConfig):
            # Check to see if it's a file path
            with open(config, 'r') as source_file_fh:
                self.config = PrimaryFileConfig(
                    **yaml.load(source_file_fh, Loader=UniqueIncludeLoader)
                )
        else:
            # TODO better error handling
            self.config = config

        for file in config.files:
            resource_io = open_resource(file, config.compression)
            if self.config.format == 'csv':
                self._readers.append(
                    CSVReader(
                        resource_io,
                        name=config.name,
                        field_type_map=config.field_type_map,
                        delimiter=config.delimiter,
                        header_delimiter=config.header_delimiter,
                        header=config.header,
                        comment_char=self.config.comment_char,
                        row_limit = self.row_limit
                    )
                )
            elif self.config.format == 'jsonl':
                self._readers.append(
                    JSONLReader(
                        resource_io,
                        name=config.name,
                        required_properties=config.required_properties,
                        row_limit = self.row_limit
                    )
                )
            elif self.config.format == 'json' or self.config.format == 'yaml':
                self._readers.append(
                    JSONReader(
                        resource_io,
                        name=config.name,
                        json_path=config.json_path,
                        required_properties=config.required_properties,
                        is_yaml=(self.config.format == 'yaml'),
                        row_limit = self.row_limit
                    )
                )
            else:
                raise ValueError(f"File type {format} not supported")

    def __iter__(self) -> Iterator:
        return self

    def __next__(self) -> Dict[str, Any]:
        if self._reader is None:
            self._reader = self._readers.pop()
        try:
            row = self._get_row()
        except StopIteration as si:
            if len(self._readers) == 0:
                raise si
            else:
                self._reader = self._readers.pop()
                row = self._get_row()
        return row

    def _get_row(self):
        if self._filter:
            row = next(self._reader)
            while not self._filter.include_row(row):
                # TODO log filtered out lines
                row = next(self._reader)
        else:
            row = next(self._reader)
        # Retain the most recent row so that it can be logged alongside validation errors
        self.last_row = row
        return row
