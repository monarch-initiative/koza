from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Union

import yaml

from koza.io.reader.csv_reader import CSVReader
from koza.io.reader.json_reader import JSONReader
from koza.io.reader.jsonl_reader import JSONLReader
from koza.io.utils import open_resource
from koza.model.config.source_config import DatasetDescription, MapFileConfig, PrimaryFileConfig
from koza.model.translation_table import TranslationTable
from koza.row_filter import RowFilter


class SourceFile:
    """
    An iterator that provides a layer of abstraction over file types
    and adds filter support to the readers in io.reader

    config: Source config
    reader: An iterator that takes in an IO[str] as its first argument
    and yields a dictionary
    """

    def __init__(self, config: Union[PrimaryFileConfig, MapFileConfig]):

        self.config = config
        self._filter = RowFilter(config.filters)
        self._reader = None
        self._readers: List = []
        self.last_row: Optional[Dict] = None

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
                        has_header=config.has_header,
                        skip_lines=config.skip_lines,
                    )
                )
            elif self.config.format == 'jsonl':
                self._readers.append(
                    JSONLReader(
                        resource_io,
                        name=config.name,
                        required_properties=config.required_properties,
                    )
                )
            elif self.config.format == 'json':
                self._readers.append(
                    JSONReader(
                        resource_io,
                        name=config.name,
                        json_path=config.json_path,
                        required_properties=config.required_properties,
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


@dataclass(init=False)
class Source:
    """
    For simplicity copying over all the fields
    from source_config.SourceConfig

    avoids nesting but also a DRY violation?
    """

    source_files: List[SourceFile]
    name: str = None
    dataset_description: DatasetDescription = None
    translation_table: TranslationTable = None

    def __init__(
        self,
        source_files: List[Union[str, SourceFile]],
        name: str = None,
        dataset_description: DatasetDescription = None,
        translation_table: TranslationTable = None,
    ):
        self.name = name
        self.dataset_description = dataset_description
        self.translation_table = translation_table

        tmp_source_file = []
        for source_file in source_files:
            if not isinstance(source_file, SourceFile):
                with open(source_file, 'r') as source_file_fh:
                    source_file_config = PrimaryFileConfig(**yaml.safe_load(source_file_fh))
                    source_file_config.path = source_file
                    tmp_source_file.append(SourceFile(source_file_config))
            else:
                tmp_source_file.append(source_file)

        self.source_files = tmp_source_file
