import re
import logging

from koza.curie_util import get_curie_map

curie_regexp = re.compile(r'^[a-zA-Z_]?[a-zA-Z_0-9-]*:[A-Za-z0-9_][A-Za-z0-9_.-]*[A-Za-z0-9_]*$')

LOG = logging.getLogger(__name__)


class Curie(str):
    """
    A curie formatted string, see https://www.w3.org/TR/curie/

    This class is set up to work with pydantic, see
    https://pydantic-docs.helpmanual.io/usage/types/#custom-data-types
    """

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(
            pattern=curie_regexp,
            examples=['foo:bar', 'HP:0000001'],
        )

    @classmethod
    def validate(cls, curie):
        if not isinstance(curie, str):
            raise TypeError('string required')
        if not Curie.is_prefix_in_map(curie):
            prefix = curie.split(':')[0]
            LOG.warning(f"prefix: '{prefix}' is not in curie map")
            # raise ValueError(f"prefix: '{prefix}' is not in curie map")
        return curie

    @staticmethod
    def is_prefix_in_map(curie: str) -> bool:

        curie_map = get_curie_map()

        prefix = curie.split(":")[0]

        if prefix not in curie_map.keys():
            return False

        return True
