from dataclasses import field
from pydantic.dataclasses import dataclass
from pydantic import validator
from typing import List, Union, ClassVar

from ..curie import Curie


class PydanticConfig:
    validate_assignment = True
    validate_all = True
    underscore_attrs_are_private = True
    extra = 'forbid'


@dataclass(config=PydanticConfig)
class Entity:
    """
    Root Biolink Model class for all things and informational relationships, real or imagined
    """
    id: Curie = None
    name: str = ''
    category: List[str] = field(default_factory=list)
    iri: str = None
    type: str = None
    description: str = None
    source: str = None
    provided_by: Union[str, List[str]] = field(default_factory=list)

    # converters
    @validator('provided_by')
    def convert_scalar_to_list(cls, provided_by):
        if isinstance(provided_by, str):
            provided_by = [provided_by]
        return provided_by
