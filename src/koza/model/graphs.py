
from biolink_model.datamodel.pydanticmodel_v2 import NamedThing, Association
from dataclasses import dataclass
from typing import Iterable


@dataclass
class KnowledgeGraph:
    nodes: Iterable[NamedThing] | None = None
    edges: Iterable[Association] | None = None

    def __post_init__(self):
        if self.nodes is None:
            self.nodes = []
        if self.edges is None:
            self.edges = []