import re

from koza.curie_util import get_curie_map

curie_regexp = re.compile(r'^[a-zA-Z_]?[a-zA-Z_0-9-]*:[A-Za-z0-9_][A-Za-z0-9_.-]*[A-Za-z0-9_]*$')


class Curie(str):
    """
    A curie formatted string, see https://www.w3.org/TR/curie/

    This class is set up to work with pydantic, see
    https://pydantic-docs.helpmanual.io/usage/types/#custom-data-types

    Note this class should only be used in pydantic models, as it otherwise
    does not validate the input string, eg
    curie = Curie('this is not a curie')
    does not run the validate function on 'this is not a curie'
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
            raise ValueError(f"prefix: '{prefix}' is not in curie map")
        return curie

    @staticmethod
    def is_prefix_in_map(curie: str) -> bool:

        curie_map = get_curie_map()

        prefix = curie.split(":")[0]

        if prefix not in curie_map.keys():
            return False

        return True
