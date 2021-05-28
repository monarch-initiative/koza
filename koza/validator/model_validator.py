"""
Module for storing reused pydantic validators
See https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators

These also function as converters
"""
from typing import List, Union

from pydantic import validator as pydantic_validator

from koza.model.biolink.entity import Entity

TAXON_PREFIX = ['NCBITaxon']

# the latest definition of publication is too broad
# to constrain to a prefix
# PUBLICATION_PREFIX = []


def _curie_must_have_prefix(curie: str, prefix_filter: List[str]) -> str:
    prefix = curie.split(':')[0]
    if prefix not in prefix_filter:
        raise ValueError(f"'{prefix}:' prefix is not valid, valid prefixes are {prefix_filter}")
    return curie


def _all_curies_must_have_prefix(curies: List[str], prefix: List[str]) -> List[str]:
    for curie in curies:
        _curie_must_have_prefix(curie, prefix)
    return curies


def _valid_taxon(curies: List[str]) -> List[str]:
    return _all_curies_must_have_prefix(curies, TAXON_PREFIX)


def valid_taxon(field: str) -> classmethod:
    decorator = pydantic_validator(field, allow_reuse=True)
    validator = decorator(_valid_taxon)
    return validator


def _convert_object_to_scalar(field: Union[Entity, str]) -> str:
    if isinstance(field, Entity):
        return field.id
    else:
        return field


def convert_object_to_scalar(field: str) -> classmethod:
    decorator = pydantic_validator(field, allow_reuse=True)
    validator = decorator(_convert_object_to_scalar)
    return validator


def _convert_objects_to_scalars(field: List[Union[Entity, str]]) -> List[str]:
    return [_convert_object_to_scalar(obj) for obj in field]


def convert_objects_to_scalars(field: str) -> classmethod:
    decorator = pydantic_validator(field, allow_reuse=True)
    validator = decorator(_convert_objects_to_scalars)
    return validator
