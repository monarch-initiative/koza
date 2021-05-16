import inspect
from dataclasses import field
from typing import List, Union

from pydantic.dataclasses import dataclass

from koza.model.config.pydantic_config import PydanticConfig
from koza.model.curie import Curie
from koza.validator.model_validator import convert_scalar_to_list, convert_str_to_curie


@dataclass(config=PydanticConfig)
class Entity:
    """
    Root Biolink Model class for all things and informational relationships, real or imagined
    """

    id: Union[Curie, str] = None
    name: str = ''
    category: List[str] = field(default_factory=list)
    iri: str = None
    type: str = None
    description: str = None
    source: str = None
    provided_by: Union[str, List[str]] = field(default_factory=list)

    # converters
    _convert_str_to_curie = convert_str_to_curie('id')
    _convert_provided_by = convert_scalar_to_list('provided_by')

    def __post_init__(self):
        # Initialize default categories if not set
        # by traversing the MRO chain
        if not self.category:
            self.category = [
                super_class._category
                for super_class in inspect.getmro(type(self))
                if hasattr(super_class, '_category')
            ]
