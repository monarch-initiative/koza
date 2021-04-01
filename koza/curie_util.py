"""
Utility functions for loading a curie map from a
yaml configuration, checking for duplicate keys
and that the map is a bimap then converting to a dictionary

relocate to a util module?
"""
import json
from enum import Enum
from functools import lru_cache
from os import PathLike
from typing import IO, Dict

import yaml
from yaml.constructor import ConstructorError

from koza.io.utils import open_resource

from .validator.map_validator import is_dictionary_bimap

DEFAULT_CURIE_MAP = 'https://raw.githubusercontent.com/biolink/biolink-model/master/context.jsonld'


class CurieFileFormat(Enum):
    yaml = 1
    jsonld = 2


class UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        mapping = []
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ConstructorError(
                    f"while constructing a mapping for {value_node.value} "
                    f"found duplicate key {key}"
                )
            mapping.append(key)
        return super().construct_mapping(node, deep)


@lru_cache(maxsize=2)
def get_curie_map(
    curie_path: PathLike = None,
    curie_format: CurieFileFormat = CurieFileFormat.yaml,
    enforce_bimap: bool = True,
) -> Dict[str, str]:
    """
    Get a local or remote curie map and convert to a dict
    :param curie_path:
    :param curie_format:
    :param enforce_bimap:
    :return:
    """

    if not curie_path:
        curie_path = DEFAULT_CURIE_MAP
        curie_format = CurieFileFormat.jsonld
        enforce_bimap = False

    with open_resource(curie_path) as curie_fh:
        if curie_format == CurieFileFormat.yaml:
            curie_map = _curie_map_from_yaml(curie_fh)

        elif curie_format == CurieFileFormat.jsonld:
            curie_map = _curie_map_from_jsonld(curie_fh)

        else:
            raise ValueError(f"Unsupported curie format: {CurieFileFormat.name}")

    if enforce_bimap and not is_dictionary_bimap(curie_map):
        raise ValueError("Global table is not a bimap")

    return curie_map


def _curie_map_from_yaml(curie_io: IO[str]) -> Dict[str, str]:
    """
    Process a io stream from a curie yaml and return
    a dictionary
    :param curie_io: io stream from open(curie_map_yaml)
    :return: Dictionary of prefix: reference
    """
    return yaml.load(curie_io, Loader=UniqueKeyLoader)


def _curie_map_from_jsonld(curie_io: IO[str]) -> Dict[str, str]:
    """
    Process a io stream from a jsonld @context and return a dictionary
    :param curie_io: io stream from open(curie_map_yaml)
    :return: Dictionary of prefix: reference
    """
    curie_map = {}
    jsonld = json.load(curie_io)
    if '@context' in jsonld:
        for key, val in jsonld['@context'].items():
            if isinstance(key, str) and isinstance(val, str) and not key.startswith('@'):
                curie_map[key] = val
    else:
        pass  # raise exception?

    return curie_map
