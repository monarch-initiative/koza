from typing import Iterable, IO, Dict, Any

from csv import DictReader

from bioweave.io.reader.reader import BioWeaveReader


class CSVReader(BioWeaveReader, DictReader):
    type_map: Dict[str, Any]

    def __init__(self, file_handle):
        pass

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.reader)
