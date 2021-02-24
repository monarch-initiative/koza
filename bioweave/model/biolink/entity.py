import inspect
from dataclasses import field
from typing import List, Union

from pydantic import validator
from pydantic.dataclasses import dataclass

from ..config.pydantic_config import PydanticConfig
from ..curie import Curie


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

    def __post_init__(self):
        # Initialize default categories if not set
        # by traversing the MRO chain
        if not self.category:
            self.category = [
                super_class._category
                for super_class in inspect.getmro(type(self))
                if hasattr(super_class, '_category')
            ]
