from typing import Iterable, IO, Dict, Any
from abc import ABC
from dataclasses import dataclass

from csv import DictReader


@dataclass
class BioWeaveReader(ABC, Iterable):
    file_handle: IO[str]
    reader: Iterable
