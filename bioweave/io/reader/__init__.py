"""
Do we need an abstract base class
for an iterator with a __next__ that returns a Dict

eg
from abc import ABC, abstractmethod
from typing import IO, Iterator, Dict, Any


class BioWeaveReader(ABC, Iterator):
    '''
    An abstract base class for an Iterable that contains a function
    called reader that returns an iterator
    '''

    #def reader(self, file: Iterable[IO[str]], *args: Any, **kwargs: Any) -> Iterator[Any]:
    #    raise NotImplementedError

    @abstractmethod
    def __init__(self, io_str: IO[str]):
        self.io_str = io_str

    def __iter__(self) -> Iterator:
        return self

    @abstractmethod
    def __next__(self) -> Dict[str, Any]:
        raise NotImplementedError

Seems like unnecessary complexity, and python doesn't enforce the init
so it's a bit pointless

Easy enough to require any bioweavereader to be a Iterator[Dict[str, Any]] and document
that the first arg should be an IO[str]
"""