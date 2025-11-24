from pydantic.dataclasses import dataclass

from koza.model.config.pydantic_config import PYDANTIC_CONFIG
from koza.model.config.sssom_config import SSSOMConfig
from koza.model.formats import OutputFormat


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class WriterConfig:
    format: OutputFormat = OutputFormat.tsv
    sssom_config: SSSOMConfig | None = None
    node_properties: list[str] | None = None
    edge_properties: list[str] | None = None
    min_node_count: int | None = None
    min_edge_count: int | None = None
    max_node_count: int | None = None
    max_edge_count: int | None = None
