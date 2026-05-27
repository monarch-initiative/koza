from abc import ABC, abstractmethod
from collections.abc import Iterable


class KozaWriter(ABC):
    """
    An abstract base class for all koza writers

    # @abstractmethod
    # def writeheader(self) -> Optional[int]:
    #     pass
    """

    @abstractmethod
    def write(self, entities: Iterable):
        pass

    @abstractmethod
    def write_nodes(self, nodes: Iterable):
        pass

    @abstractmethod
    def write_edges(self, edges: Iterable):
        pass

    @abstractmethod
    def finalize(self):
        pass

    def result(self):
        raise NotImplementedError()
