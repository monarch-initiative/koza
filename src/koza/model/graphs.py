
from biolink_model.datamodel.pydanticmodel_v2 import NamedThing, Association
from dataclasses import dataclass
from typing import Iterable


@dataclass
class KnowledgeGraph:
    nodes: Iterable[NamedThing] | None = None
    edges: Iterable[Association] | None = None