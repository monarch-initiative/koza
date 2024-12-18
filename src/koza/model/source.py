from tarfile import TarFile
from typing import Any, Dict, Iterable, List, Optional, TextIO, Union
from zipfile import ZipFile

from koza.io.reader.csv_reader import CSVReader
from koza.io.reader.json_reader import JSONReader
from koza.io.reader.jsonl_reader import JSONLReader
from koza.io.utils import open_resource
from koza.model.config.source_config import FormatType, KozaConfig
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
        self._opened: list[Union[ZipFile, TarFile, TextIO]] = []

        for file in reader_config.files:
            opened_resource = open_resource(file)
            if isinstance(opened_resource, tuple):
                archive, resources = opened_resource
                self._opened.append(archive)
            else:
                resources = [opened_resource]

            for resource in resources:
                self._opened.append(resource.reader)
                if reader_config.format == FormatType.csv:
                    self._readers.append(
                        CSVReader(
                            resource.reader,
                            config=reader_config,
                            row_limit=self.row_limit,
                        )
                    )
                elif reader_config.format == FormatType.jsonl:
                    self._readers.append(
                        JSONLReader(
                            resource.reader,
                            config=reader_config,
                            row_limit=self.row_limit,
                        )
                    )
                elif reader_config.format == FormatType.json or reader_config.format == FormatType.yaml:
                    self._readers.append(
                        JSONReader(
                            resource.reader,
                            config=reader_config,
                            row_limit=self.row_limit,
                        )
                    )
                else:
                    raise ValueError(f"File type {reader_config.format} not supported")

    def __iter__(self):
        for reader in self._readers:
            for item in reader:
                if self._filter and not self._filter.include_row(item):
                    continue
                self.last_row = item
                yield item

        for fh in self._opened:
            fh.close()
