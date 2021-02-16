from dataclasses import dataclass
from typing import Dict, Iterator, Any

#from bioweave.io.reader import BioWeaveReader  # see reader.__init__.py
from .config.source_config import SourceConfig
from .translation_table import TranslationTable


@dataclass(frozen=True)
class Source:
    """
    reader: An iterator that takes in an IO[str] as its first argument
    and yields a dictionary
    """

    reader: Iterator[Dict[str, Any]]
    config: SourceConfig


@dataclass(frozen=True)
class PrimarySource(Source):

    translation_table: TranslationTable
