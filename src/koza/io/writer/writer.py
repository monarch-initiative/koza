from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Union, Tuple

from koza.converter.kgx_converter import KGXConverter
from koza.model.config.sssom_config import SSSOMConfig


class KozaWriter(ABC):
    """
    An abstract base class for all koza writers
    """

    def __init__(
        self,
        output_dir: Union[str, Path],
        source_name: str,
        node_properties: List[str] = None,
        edge_properties: List[str] = None,
        sssom_config: SSSOMConfig = None,
    ):
        self.output_dir = output_dir
        self.source_name = source_name
        self.node_columns = node_properties
        self.edge_columns = edge_properties
        self.sssom_config = sssom_config

        self.converter = KGXConverter()

    def write(self, entities: Iterable, skip_checks: bool = False):
        nodes, edges = self.converter.convert(entities)

        if nodes:
            for node in nodes:
                self.check_extra_fields(tuple(node.keys()), tuple(self.node_columns))
                self.write_node(node)

        if edges:
            for edge in edges:
                if self.sssom_config:
                    edge = self.sssom_config.apply_mapping(edge)
                self.check_extra_fields(tuple(edge.keys()), tuple(self.edge_columns))
                self.write_edge(edge)

    @staticmethod
    @lru_cache(maxsize=None)
    def check_extra_fields(row_keys: Tuple, columns: Tuple) -> None:
        """
        Check for extra fields in the row that are not in the columns
        """

        extra_fields = not set(row_keys).issubset(set(columns))
        if extra_fields:
            raise ValueError(f"Extra fields found in row: {sorted(set(row_keys) - set(columns))}")

    @abstractmethod
    def write_edge(self, edge: dict):
        pass

    @abstractmethod
    def write_node(self, node: dict):
        pass

    @abstractmethod
    def finalize(self):
        pass
