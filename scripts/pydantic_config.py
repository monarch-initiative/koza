"""
Module for storing reused pydantic validators
See https://pydantic-docs.helpmanual.io/usage/validators/#reuse-validators

These also function as converters
"""
import logging
from typing import Any, List

from pydantic import validator as pydantic_validator

LOG = logging.getLogger(__name__)


class PydanticConfig:
    """
    Pydantic config
    https://pydantic-docs.helpmanual.io/usage/model_config/
    """

    validate_assignment = True
    validate_all = True
    underscore_attrs_are_private = True
    extra = 'forbid'
    arbitrary_types_allowed = True  # TODO re-evaluate this


def check_curie_prefix(curie: str, prefix_filter: List[str]) -> str:
    prefix = curie.split(':')[0]
    if prefix not in prefix_filter:
        LOG.warning(f"{curie} is not prefixed with {prefix_filter}")
    return curie


def _convert_scalar_to_list(field: Any) -> List[str]:
    if isinstance(field, list):
        field = [field]
    return field


def convert_scalar_to_list(field: str) -> classmethod:
    decorator = pydantic_validator(field, allow_reuse=True)
    validator = decorator(_convert_scalar_to_list)
    return validator
