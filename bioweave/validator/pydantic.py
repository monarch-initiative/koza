"""
Module for storing reused pydantic validators
See https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators
"""
from typing import Union, List
from ..model import Entity
from .map_validator import is_valid_curie

TAXON_PREFIX = ['NCBITaxon']

# It seems the latest definition of publication is too broad
# to constrain to a prefix
# PUBLICATION_PREFIX = []


def field_must_be_curie(field: str) -> str:
    if not is_valid_curie(field):
        raise ValueError(f"{field} is not a curie")
    return field


def list_field_are_curies(items: List[str]) -> List[str]:
    for curie in items:
        field_must_be_curie(curie)
    return items


def convert_object_to_scalar(field: Union[Entity, str]) -> str:
    if isinstance(field, Entity):
        return field.id
    else:
        return field


def convert_objects_to_scalars(fields: List[Union[Entity, str]]) -> List[str]:
    return [convert_object_to_scalar(field) for field in fields]


def curie_must_have_prefix(curie: str, prefix: List[str]) -> str:
    if not is_valid_curie(curie, prefix):
        raise ValueError(f"{curie} is not prefixed with {prefix}")
    return curie


def all_curies_must_have_prefix(curies: List[str], prefix: List[str]) -> List[str]:
    for curie in curies:
        curie_must_have_prefix(curie, prefix)
    return curies


def valid_taxon(curies: List[str]) -> List[str]:
    return all_curies_must_have_prefix(curies, TAXON_PREFIX)

def get_default_categories():
    pass