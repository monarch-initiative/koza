from tarfile import TarFile
from typing import Any, Dict, Iterable, List, Optional, TextIO, Union
from zipfile import ZipFile

from loguru import logger
from tqdm import tqdm

from koza.io.reader.csv_reader import CSVReader
from koza.io.reader.json_reader import JSONReader
from koza.io.reader.jsonl_reader import JSONLReader
from koza.io.utils import open_resource
from koza.model.formats import InputFormat
from koza.model.koza import KozaConfig
from koza.utils.row_filter import RowFilter


class Source:
    """
    Source class for files and maps

    Source is an iterator that provides a layer of abstraction over file types
    and adds filter support to the readers in io.reader

    config: Source config
    row_limit: Number of rows to process
    reader: An iterator that takes in an IO[str] and yields a dictionary
    """

    def __init__(self, config: KozaConfig, row_limit: int = 0, show_progress: bool = False):
        reader_config = config.reader

        self.row_limit = row_limit
        self.show_progress = show_progress
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
                if reader_config.format == InputFormat.csv:
                    self._readers.append(
                        CSVReader(
                            resource.reader,
                            config=reader_config,
                        )
                    )
                elif reader_config.format == InputFormat.jsonl:
                    self._readers.append(
                        JSONLReader(
                            resource.reader,
                            config=reader_config,
                        )
                    )
                elif reader_config.format == InputFormat.json or reader_config.format == InputFormat.yaml:
                    self._readers.append(
                        JSONReader(
                            resource.reader,
                            config=reader_config,
                        )
                    )
                else:
                    raise ValueError(f"File type {reader_config.format} not supported")

    def __iter__(self):
        num_rows = 0

        for reader in self._readers:
            pbar: Optional[tqdm[dict[str, Any]]] = None
            numlines = 0

            if self.show_progress and isinstance(reader, CSVReader):
                reader.header  # noqa: B018
                numlines = sum(1 for _ in reader.io_str)
                pbar = tqdm(reader, total=numlines, leave=True)
                reader.reset()

            if self.show_progress and isinstance(reader, JSONLReader):
                numlines = sum(1 for _ in reader.io_str)
                reader.io_str.seek(0)
                pbar = tqdm(reader, total=numlines, leave=True)

            for item in reader:
                if pbar is not None:
                    pbar.update(1)

                if self._filter and not self._filter.include_row(item):
                    continue

                self.last_row = item

                yield item

                num_rows += 1
                if self.row_limit and num_rows == self.row_limit:
                    logger.info(f"Reached row limit {self.row_limit} (read {num_rows})")
                    break

            else:
                # If this reader was consumed without breaking, continue on to the next reader
                continue

            # If it did break (i.e. it reached its row limit), then do not proceed to the next reader
            break

        for fh in self._opened:
            fh.close()
