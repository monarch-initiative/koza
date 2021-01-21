from dataclasses import dataclass

from bioweave.reader.reader import BioWeaveReader
from .config.source_config import SourceConfig
from .translation_table import TranslationTable


@dataclass(frozen=True)
class Source:

    reader: BioWeaveReader
    config: SourceConfig


@dataclass(frozen=True)
class PrimarySource(Source):

    translation_table: TranslationTable
