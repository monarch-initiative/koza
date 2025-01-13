from typing import List, Optional

from koza.model.config.pydantic_config import PYDANTIC_CONFIG
from koza.model.config.sssom_config import SSSOMConfig
from koza.model.formats import OutputFormat
from pydantic.dataclasses import dataclass


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class WriterConfig:
    format: OutputFormat = OutputFormat.tsv
    sssom_config: Optional[SSSOMConfig] = None
    node_properties: Optional[List[str]] = None
    edge_properties: Optional[List[str]] = None
    min_node_count: Optional[int] = None
    min_edge_count: Optional[int] = None
