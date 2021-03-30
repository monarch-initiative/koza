from dataclasses import dataclass
from typing import Dict

from koza.model.config.koza_config import KozaConfig
from koza.model.source import Source


@dataclass(init=False, frozen=True)
class KozaApp:
    """
    Class that holds all configuration information
    for Koza

    Note that this is intended to be a singleton
    that is instantiated in biolink_runner and that
    object either imported in other modules, or
    passed in via a function

    Note that this borders on some anti-patterns
    - singleton as global
    - god object

    So this particular code should be re-evaluated post prototype

    Hoping that making all attributes read-only offsets some downsides
    of this approach (multi threading would be fine)
    """

    config: KozaConfig
    curie_map: Dict[str, str] = None
    source_registry: Dict[str, Source] = None
    map_registry: Dict[str, Source] = None
    # serializer_registry: Dict[str, SerializerConfig] = None
    # map_cache: Dict[str, Dict] = None

    def __init__(self, config: KozaConfig):
        pass
