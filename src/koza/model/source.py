from typing import Any, Dict, Iterable, List, Optional

from koza.io.reader.csv_reader import CSVReader
from koza.io.reader.json_reader import JSONReader
from koza.io.reader.jsonl_reader import JSONLReader
from koza.io.utils import open_resource
from koza.model.config.source_config import KozaConfig
from koza.utils.row_filter import RowFilter

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

    def __init__(self, config: KozaConfig, row_limit: int = 0):
        reader_config = config.reader

        self.row_limit = row_limit
        self._filter = RowFilter(config.transform.filters)
        self._reader = None
        self._readers: List[Iterable[Dict[str, Any]]] = []
        self.last_row: Optional[Dict[str, Any]] = None

        for file in reader_config.files:
            resource_io = open_resource(file)
            if reader_config.format == "csv":
                self._readers.append(
                    CSVReader(
                        resource_io,
                        config=reader_config,
                        row_limit=self.row_limit,
                    )
                )
            elif reader_config.format == "jsonl":
                self._readers.append(
                    JSONLReader(
                        resource_io,
                        config=reader_config,
                        row_limit=self.row_limit,
                    )
                )
            elif reader_config.format == "json" or reader_config.format == "yaml":
                self._readers.append(
                    JSONReader(
                        resource_io,
                        config=reader_config,
                        row_limit=self.row_limit,
                    )
                )
            else:
                raise ValueError(f"File type {format} not supported")

    def __iter__(self):
        for reader in self._readers:
            for item in reader:
                if self._filter and not self._filter.include_row(item):
                    continue
                self.last_row = item
                yield item
