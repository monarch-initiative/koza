from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional

from koza.model.biolink.entity import Entity


class KozaWriter(ABC):
    """
    An abstract base class for all koza writers

    # @abstractmethod
    # def writeheader(self) -> Optional[int]:
    #     pass
    """

    @abstractmethod
    def write(self, entities: Iterable[Entity]):
        pass

    @abstractmethod
    def finalize(self):
        pass

    @abstractmethod
    def writerow(self, row: Iterable[Any]) -> Optional[int]:
        pass

    @abstractmethod
    def writerows(self, rows: Iterable[Iterable[Any]]) -> Optional[int]:
        pass
