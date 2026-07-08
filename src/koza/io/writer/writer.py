from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import TYPE_CHECKING

from koza.utils.exceptions import CountValidationError

if TYPE_CHECKING:
    from koza.model.writer import WriterConfig


class KozaWriter(ABC):
    """
    An abstract base class for all koza writers

    # @abstractmethod
    # def writeheader(self) -> Optional[int]:
    #     pass
    """

    #: Set by concrete writers so count validation can read the configured bounds.
    #: Left as None (the default) by writers without a config, e.g. PassthroughWriter.
    config: "WriterConfig | None" = None
    #: Running tallies of rows written, maintained by concrete writers.
    node_count: int = 0
    edge_count: int = 0

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

    def validate_counts(self) -> None:
        """Enforce the writer's configured min/max node and edge counts.

        A no-op when no config (or no bound) is set. Raises CountValidationError
        naming every violated bound so a build fails loudly rather than shipping a
        silently truncated graph.
        """
        config = self.config
        if config is None:
            return

        violations: list[str] = []
        for label, count, minimum, maximum in (
            ("node", self.node_count, config.min_node_count, config.max_node_count),
            ("edge", self.edge_count, config.min_edge_count, config.max_edge_count),
        ):
            if minimum is not None and count < minimum:
                violations.append(f"{label} count {count} is below the configured min_{label}_count of {minimum}")
            if maximum is not None and count > maximum:
                violations.append(f"{label} count {count} is above the configured max_{label}_count of {maximum}")

        if violations:
            raise CountValidationError("; ".join(violations))

    def result(self):
        raise NotImplementedError()
