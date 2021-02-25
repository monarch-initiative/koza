from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional


class KozaWriter(ABC):
    """
    An abstract base class for all koza writers
    """

    @abstractmethod
    def writeheader(self) -> Optional[int]:
        pass

    @abstractmethod
    def writerow(self, row: Iterable[Any]) -> Optional[int]:
        pass

    @abstractmethod
    def writerows(self, rows: Iterable[Iterable[Any]]) -> Optional[int]:
        pass
