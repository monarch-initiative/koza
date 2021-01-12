from dataclasses import dataclass
from typing import Dict

from .model.config.bioweave_config import BioWeaveConfig


@dataclass
class BioWeave:
    """

    """
    config: BioWeaveConfig
    source_registry: Dict[str, str]
    map_registry: Dict[str, Dict]
    curie_map: Dict[str, str]

    def serialize(self, ingest_name: str, *args):
        pass