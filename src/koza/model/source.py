import glob as glob_module
from collections.abc import Iterable
from pathlib import Path
from tarfile import TarFile
from typing import Any, TextIO
from zipfile import ZipFile

from loguru import logger
from tqdm import tqdm

from koza.io.reader.csv_reader import CSVReader
from koza.io.reader.json_reader import JSONReader
from koza.io.reader.jsonl_reader import JSONLReader
from koza.io.utils import open_resource
from koza.model.formats import InputFormat
from koza.model.reader import ReaderConfig
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

    def __init__(
        self,
        config: ReaderConfig,
        base_directory: Path,
        row_limit: int = 0,
        show_progress: bool = False,
    ):
        self.reader_config = config
        self.base_directory = base_directory

        self.row_limit = row_limit
        self.show_progress = show_progress
        self._filter = RowFilter(config.filters)
        self._reader = None
        self._readers: list[Iterable[dict[str, Any]]] = []
        self.last_row: dict[str, Any] | None = None
        self._opened: list[ZipFile | TarFile | TextIO] = []

    def _expand_file_patterns(self, patterns: list[str]) -> list[Path]:
        """Expand glob patterns in file list and return resolved paths.

        Supports glob patterns: *, ?, [abc], ** (recursive)

        Args:
            patterns: List of file paths or glob patterns

        Returns:
            List of resolved Path objects, sorted alphabetically
        """
        expanded_files: list[Path] = []
        for pattern in patterns:
            pattern_path = Path(pattern)
            if not pattern_path.is_absolute():
                pattern_path = self.base_directory / pattern_path

            pattern_str = str(pattern_path)

            # Check for glob characters
            if any(c in pattern_str for c in ["*", "?", "[", "]"]):
                matches = sorted(glob_module.glob(pattern_str, recursive=True))
                if matches:
                    expanded_files.extend(Path(m) for m in matches)
                else:
                    # No matches - treat as literal (will fail at open_resource)
                    expanded_files.append(pattern_path)
            else:
                expanded_files.append(pattern_path)

        return expanded_files

    def _open_files(self):
        # Handle file_archive separately from regular files
        # If file_archive is specified, open it and filter files from it
        # Otherwise, open files directly
        if self.reader_config.file_archive:
            archive_path = Path(self.reader_config.file_archive)
            if not archive_path.is_absolute():
                archive_path = self.base_directory / archive_path

            opened_resource = open_resource(archive_path)
            if isinstance(opened_resource, tuple):
                archive, resources = opened_resource
                self._opened.append(archive)

                # Filter resources if files list is provided
                for resource in resources:
                    # If files list is specified, only process matching files
                    if self.reader_config.files and resource.name not in self.reader_config.files:
                        continue

                    self._opened.append(resource.reader)
                    if self.reader_config.format == InputFormat.csv:
                        self._readers.append(
                            CSVReader(
                                resource.reader,
                                config=self.reader_config,
                            )
                        )
                    elif self.reader_config.format == InputFormat.jsonl:
                        self._readers.append(
                            JSONLReader(
                                resource.reader,
                                config=self.reader_config,
                            )
                        )
                    elif self.reader_config.format == InputFormat.json or self.reader_config.format == InputFormat.yaml:
                        self._readers.append(
                            JSONReader(
                                resource.reader,
                                config=self.reader_config,
                            )
                        )
                    else:
                        raise ValueError(f"File type {self.reader_config.format} not supported")
        else:
            # Process regular files with glob expansion
            expanded_files = self._expand_file_patterns(self.reader_config.files)
            for file_path in expanded_files:
                opened_resource = open_resource(file_path)
                if isinstance(opened_resource, tuple):
                    archive, resources = opened_resource
                    self._opened.append(archive)
                else:
                    resources = [opened_resource]

                for resource in resources:
                    self._opened.append(resource.reader)
                    if self.reader_config.format == InputFormat.csv:
                        self._readers.append(
                            CSVReader(
                                resource.reader,
                                config=self.reader_config,
                            )
                        )
                    elif self.reader_config.format == InputFormat.jsonl:
                        self._readers.append(
                            JSONLReader(
                                resource.reader,
                                config=self.reader_config,
                            )
                        )
                    elif self.reader_config.format == InputFormat.json or self.reader_config.format == InputFormat.yaml:
                        self._readers.append(
                            JSONReader(
                                resource.reader,
                                config=self.reader_config,
                            )
                        )
                    else:
                        raise ValueError(f"File type {self.reader_config.format} not supported")

    def __iter__(self):
        self._open_files()
        num_rows = 0

        for reader in self._readers:
            pbar: tqdm[dict[str, Any]] | None = None
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
