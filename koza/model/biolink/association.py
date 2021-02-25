"""
Biolink Model Dataclasses + Pydantic validators

Longer term generate this from Biolink model yaml
https://github.com/biolink/biolink-model/blob/master/biolink-model.yaml

"""

from dataclasses import field
from typing import ClassVar

from pydantic.dataclasses import dataclass

from koza.validator.model_validator import *

from ..config.pydantic_config import PydanticConfig
from ..curie import Curie
from .named_thing import Entity, Publication


@dataclass(config=PydanticConfig)
class Association(Entity):
    """
    A typed association between two entities, supported by evidence
    """

    _category: ClassVar[str] = 'Association'

    subject: Union[Entity, Curie] = None
    predicate: Union[Entity, Curie] = None
    object: Union[Entity, Curie] = None
    relation: str = None
    negated: bool = False
    qualifiers: List[Curie] = field(default_factory=list)
    publications: List[Union[Publication, Curie]] = field(default_factory=list)
    type: Curie = 'rdf:Statement'

    # converters
    _subject_to_scalar = convert_object_to_scalar('subject')
    _predicate_to_scalar = convert_object_to_scalar('predicate')
    _object_to_scalar = convert_object_to_scalar('object')
    _publication_to_scalar = convert_objects_to_scalars('publications')


@dataclass(config=PydanticConfig)
class GeneToGeneAssociation(Association):
    """
    abstract parent class for different kinds of gene-gene or gene product to gene product
    relationships. Includes homology and interaction.
    """

    _category: ClassVar[str] = 'GeneToGeneAssociation'


@dataclass(config=PydanticConfig)
class PairwiseGeneToGeneInteraction(GeneToGeneAssociation):
    """
    An interaction between two genes or two gene products. May be physical (e.g. protein binding)
    or genetic (between genes). May be symmetric (e.g. protein interaction) or directed (e.g. phosphorylation)
    """

    _category: ClassVar[str] = 'PairwiseGeneToGeneInteraction'
