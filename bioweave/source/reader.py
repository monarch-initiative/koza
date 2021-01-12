from typing import Iterable, IO, Dict, Any
from abc import ABC


class BioWeaveReader(ABC, Iterable):
    file_handle: IO[str]
    reader: Iterable
    type_map: Dict[str, Any]
