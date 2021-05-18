"""
Module for storing reused pydantic validators
See https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators

These also function as converters
"""
from typing import Any, List, Union

from pydantic import validator as pydantic_validator

from koza.model.curie import Curie

TAXON_PREFIX = ['NCBITaxon']

# the latest definition of publication is too broad
# to constrain to a prefix
# PUBLICATION_PREFIX = []


def _check_curie_prefix(curie: str, prefix_filter: List[str]) -> str:
    prefix = curie.split(':')[0]
    if prefix not in prefix_filter:
        raise ValueError(f"{curie} is not prefixed with {prefix}")
    return curie


def curie_must_have_prefix(
    field: Union[Curie, List[Curie]], config: List[str]
) -> Union[Curie, List[Curie]]:
    if isinstance(field, list):
        for curie in field:
            _check_curie_prefix(curie, config)
    else:
        _check_curie_prefix(field, config)
    return field


def _convert_object_to_scalar(field: Any) -> str:
    if isinstance(field, str):
        return field
    elif not field:
        return field
    else:
        try:
            field = field.id
        except AttributeError:
            pass
        return field


def convert_object_to_scalar(field: str) -> classmethod:
    decorator = pydantic_validator(field, allow_reuse=True)
    validator = decorator(_convert_object_to_scalar)
    return validator


def _convert_objects_to_scalars(field: List[Union[object, str]]) -> List[str]:
    return [_convert_object_to_scalar(obj) for obj in field]


def convert_objects_to_scalars(field: str) -> classmethod:
    decorator = pydantic_validator(field, allow_reuse=True)
    validator = decorator(_convert_objects_to_scalars)
    return validator


def _convert_scalar_to_list(field: Any) -> List[str]:
    if isinstance(field, str):
        field = [field]
    return field


def convert_scalar_to_list(field: str) -> classmethod:
    decorator = pydantic_validator(field, allow_reuse=True)
    validator = decorator(_convert_scalar_to_list)
    return validator


def _convert_str_to_curie(field: Union[str, Curie]) -> Curie:
    if field and not isinstance(field, Curie):
        field = Curie.validate(field)
        field = Curie(field)

    return field


def convert_str_to_curie(field: str) -> classmethod:
    decorator = pydantic_validator(field, allow_reuse=True)
    validator = decorator(_convert_str_to_curie)
    return validator


def _convert_list_to_curies(field: List[Union[str, Curie]]) -> List[Curie]:
    curie_list = []
    for curie in field:
        curie_list.append(_convert_str_to_curie(curie))

    return curie_list


def convert_list_to_curies(field: str) -> classmethod:
    decorator = pydantic_validator(field, allow_reuse=True)
    validator = decorator(_convert_list_to_curies)
    return validator
