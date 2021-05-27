"""
Module for storing reused pydantic validators
See https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators

These also function as converters
"""
import logging
from typing import Any, List, Union

from pydantic import validator as pydantic_validator

from koza.model.curie import Curie

LOG = logging.getLogger(__name__)

# the latest definition of publication is too broad
# to constrain to a prefix
# PUBLICATION_PREFIX = []


def check_curie_prefix(curie: str, prefix_filter: List[str]) -> str:
    prefix = curie.split(':')[0]
    if prefix not in prefix_filter:
        LOG.warning(f"{curie} is not prefixed with {prefix_filter}")
    return curie


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


def _convert_str_to_curie(field: Any) -> Any:
    if isinstance(field, str) and not isinstance(field, Curie):
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
