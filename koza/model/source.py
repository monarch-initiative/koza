from dataclasses import dataclass
from typing import Any, Dict, Iterator, List

from ..io.reader.csv_reader import CSVReader
from ..io.reader.json_reader import JSONReader
from ..io.reader.jsonl_reader import JSONLReader
from ..io.utils import open_resource
from .config.source_config import DatasetDescription, OutputFormat, SourceFileConfig
from .translation_table import TranslationTable


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
    config: Source config
    reader: An iterator that takes in an IO[str] as its first argument
    and yields a dictionary
    """

    config: SourceFileConfig
    _reader: Iterator[Dict[str, Any]]

    def __init__(self, config: SourceFileConfig):

        for file in config.files:
            with open_resource(file, config.compression) as resource_io:
                if format == 'csv':
                    self._reader = CSVReader(
                        resource_io,
                        delimiter=config.delimiter,
                        header_delimiter=config.header_delimiter,
                        name=config.name,
                    )
                elif format == 'jsonl':
                    self._reader = JSONLReader(resource_io, name=config.name)
                elif format == 'json':
                    self._reader = JSONReader(resource_io, name=config.name)
                else:
                    raise ValueError

    def __iter__(self) -> Iterator:
        return self

    def __next__(self) -> Dict[str, Any]:
        return next(self._reader)
