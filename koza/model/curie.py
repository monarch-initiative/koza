from ..validator.map_validator import curie_regexp, is_valid_curie


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
        if not is_valid_curie(curie):
            raise ValueError(f"{curie} is not a valid curie")
        return curie
