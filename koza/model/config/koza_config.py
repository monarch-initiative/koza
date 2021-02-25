from enum import Enum
from pathlib import Path
from typing import List, Union

from pydantic.dataclasses import dataclass


class SerializationEnum(str, Enum):
    """
    TODO do we need synonyms? - ttl, nt, kgx
    """

    tsv = 'tsv'
    nturtles = 'nturtles'
    # rdfstar, ntriples, etc


@dataclass(frozen=True)
class KozaConfig:
    """
    Dataclass for koza configuration
    """

    name: str
    curie_map: Union[str, Path]
    sources: List[str]
    serializations: List[SerializationEnum]
    output: str = './'
    config_dir: Union[str, Path] = None
    cache_maps: bool = True
