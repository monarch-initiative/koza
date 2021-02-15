from typing import Iterable, IO, Dict, Any, Iterator
from abc import ABC, abstractmethod
from dataclasses import dataclass

from collections.abc import Iterable

from csv import DictReader


@dataclass
class BioWeaveReader(ABC, Iterator):
    """
    An abstract base class for an Iterable that contains a function
    called reader that returns an iterator

    calling __next__ returns a dictionary

    This is modelled after the python std lib csv class:
    https://docs.python.org/3/library/csv.html
    """

    #def reader(self, file: Iterable[IO[str]], *args: Any, **kwargs: Any) -> Iterator[Any]:
    #    raise NotImplementedError

    def __iter__(self) -> Iterator:
        return self

    @abstractmethod
    def __next__(self) -> Dict[Any, Any]:
        raise NotImplementedError
