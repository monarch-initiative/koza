from dataclasses import dataclass

from bioweave.source.reader import BioWeaveReader


@dataclass(frozen=True)
class Source:

    reader: BioWeaveReader
    config: str
