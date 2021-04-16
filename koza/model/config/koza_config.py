from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Union


class SerializationEnum(str, Enum):
    """
    TODO do we need synonyms? - ttl, nt, kgx
    """

    tsv = 'tsv'
    json = 'json'
    jsonl = 'jsonl'


@dataclass(frozen=True)
class KozaConfig:
    """
    Dataclass for koza configuration
    """

    name: str = 'koza-run'
    sources: List[str] = None
    serialization: SerializationEnum = None
    output: str = './'
    config_dir: Union[str, Path] = './config'
    cache_maps: bool = True
    curie_map: Union[str, Path] = None
