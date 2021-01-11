from dataclasses import dataclass

from .reader.reader import BioWeaveReader


@dataclass(frozen=True)
class Source:

    reader: BioWeaveReader
    config: str
