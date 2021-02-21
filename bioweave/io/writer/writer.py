from abc import ABC, abstractmethod
from typing import Optional, Iterable, Any


class BioWeaveWriter(ABC):
    """
    An abstract base class for all bioweave writers
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
