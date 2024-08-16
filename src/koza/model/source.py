from typing import Any, Dict, Iterator, List, Optional, Union

from koza.io.reader.csv_reader import CSVReader
from koza.io.reader.json_reader import JSONReader
from koza.io.reader.jsonl_reader import JSONLReader
from koza.io.utils import open_resource
from koza.utils.row_filter import RowFilter
from koza.model.config.source_config import MapFileConfig, PrimaryFileConfig  # , SourceConfig

# from koza.io.yaml_loader import UniqueIncludeLoader
# import yaml


class Source:
    """
    Source class for files and maps

    Source is an iterator that provides a layer of abstraction over file types
    and adds filter support to the readers in io.reader

    config: Source config
    row_limit: Number of rows to process
    reader: An iterator that takes in an IO[str] and yields a dictionary
    """

    def __init__(self, config: Union[PrimaryFileConfig, MapFileConfig], row_limit: Optional[int] = None):
        self.config = config
        self.row_limit = row_limit
        self._filter = RowFilter(config.filters)
        self._reader = None
        self._readers: List = []
        self.last_row: Optional[Dict] = None

        for file in config.files:
            resource_io = open_resource(file)
            if self.config.format == "csv":
                self._readers.append(
                    CSVReader(
                        resource_io,
                        name=config.name,
                        field_type_map=config.field_type_map,
                        delimiter=config.delimiter,
                        header=config.header,
                        header_delimiter=config.header_delimiter,
                        header_prefix=config.header_prefix,
                        comment_char=self.config.comment_char,
                        row_limit=self.row_limit,
                    )
                )
            elif self.config.format == "jsonl":
                self._readers.append(
                    JSONLReader(
                        resource_io,
                        name=config.name,
                        required_properties=config.required_properties,
                        row_limit=self.row_limit,
                    )
                )
            elif self.config.format == "json" or self.config.format == "yaml":
                self._readers.append(
                    JSONReader(
                        resource_io,
                        name=config.name,
                        json_path=config.json_path,
                        required_properties=config.required_properties,
                        is_yaml=(self.config.format == "yaml"),
                        row_limit=self.row_limit,
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
        #If we built a filter for this source, run extra code to validate each row for inclusion in the final output.
        if self._filter:
            row = next(self._reader)
            reject_current_row = not self._filter.include_row(row)
            #If the filter says we shouldn't include the current row; we filter it out and move onto the next row.
            #We'll only break out of the following loop if "filter_current_row" is false (i.e. we have a valid row
            #to return) or we hit a StopIteration exception from self._reader.
            while reject_current_row:
                row = next(self._reader)
                reject_current_row = not self._filter.include_row(row)
        else:
            row = next(self._reader)
        # Retain the most recent row so that it can be logged alongside validation errors
        self.last_row = row
        return row
