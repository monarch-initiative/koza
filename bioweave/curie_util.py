"""
Utility functions for loading a curie map from a
yaml configuration, checking for duplicate keys
and that the map is a bimap then converting to a dictionary

relocate to a util module?
"""
# python 3.9 has a generic cache fx

from functools import lru_cache
from os import PathLike
from typing import Dict, TextIO

import yaml
from yaml.constructor import ConstructorError

try:
    pass
except ImportError:
    pass

from .validator.map_validator import is_dictionary_bimap


def no_duplicates_constructor(loader, node, deep=False):
    """
    Check for duplicate keys
    credit: https://gist.github.com/pypt/94d747fe5180851196eb

    Another option would be to use ruamel
    https://pypi.org/project/ruamel.yaml/
    """

    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        value = loader.construct_object(value_node, deep=deep)
        if key in mapping:
            raise ConstructorError(
                f"while constructing a mapping {node.start_mark} found duplicate key {key}",
                key_node.start_mark,
            )
        mapping[key] = value

    return loader.construct_mapping(node, deep)


@lru_cache
def get_curie_map(curie_path: PathLike) -> Dict[str, str]:
    with open(curie_path, 'r') as curie_fh:
        curie_map = _curie_map_from_yaml(curie_fh)

    if not is_dictionary_bimap(curie_map):
        raise ValueError("Global table is not a bimap")

    return curie_map


def _curie_map_from_yaml(curie_io: TextIO) -> Dict[str, str]:
    """
    Process a io stream from a curie yaml and return
    a dictionary
    :param curie_io: io stream from open(curie_map_yaml)
    :return: Dictionary of prefix: reference
    """
    yaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, no_duplicates_constructor)
    return yaml.safe_load(curie_io)
