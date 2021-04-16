from dataclasses import dataclass
from typing import Any, Dict, Iterator, List

from ..io.reader.csv_reader import CSVReader
from ..io.reader.json_reader import JSONReader
from ..io.reader.jsonl_reader import JSONLReader
from ..io.utils import open_resource
from .config.source_config import DatasetDescription, SourceFileConfig
from .translation_table import TranslationTable


@dataclass
class Source:
    name: str
    data_dir: str = './'
    dataset_description: DatasetDescription = None
    source_files: List[str] = None
    map_files: List[str] = None
    translation_table: TranslationTable = None


@dataclass
class SourceFile:
    """
    config: Source config
    reader: An iterator that takes in an IO[str] as its first argument
    and yields a dictionary
    """

    config: SourceFileConfig
    reader: Iterator[Dict[str, Any]]

    def __init__(self, config: SourceFileConfig):

        for file in config.files:
            with open_resource(file, config.compression) as resource_io:
                if format == 'csv':
                    self.reader = CSVReader(
                        resource_io,
                        delimiter=config.delimiter,
                        header_delimiter=config.header_delimiter,
                        name=config.name,
                    )
                elif format == 'jsonl':
                    self.reader = JSONLReader(resource_io, name=config.name)
                elif format == 'json':
                    self.reader = JSONReader(resource_io, name=config.name)
                else:
                    raise ValueError

                if format == 'csv' and config.columns is None:
                    # Iterate over the header(s) to get field names for writer
                    config.columns = next(self.reader)
