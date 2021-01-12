"""
Biolink Model Dataclasses + Pydantic validators

Longer term generate this from Biolink model yaml
https://github.com/biolink/biolink-model/blob/master/biolink-model.yaml

"""

from dataclasses import field
from pydantic.dataclasses import dataclass
from pydantic import validator
from typing import List, ClassVar, Union

from bioweave.validator import *
from .named_thing import Entity, Publication

# Type alias for use in serializers
Curie = str


@dataclass
class Association(Entity):
    """
    A typed association between two entities, supported by evidence
    """

    _label: ClassVar[str] = 'Association'
    category: ClassVar[List[str]] = ['Association']

    subject: Union[Entity, Curie] = None
    predicate: Union[Entity, Curie] = None
    object: Union[Entity, Curie] = None
    relation: str = None
    negated: bool = False
    qualifiers: List[Curie] = field(default_factory=list)
    publications: List[Union[Publication, Curie]] = field(default_factory=list)
    type: Curie = 'rdf:Statement'

    # converters
    _subject_to_scalar = validator('subject', allow_reuse=True)(convert_object_to_scalar)
    _predicate_to_scalar = validator('predicate', allow_reuse=True)(convert_object_to_scalar)
    _object_to_scalar = validator('object', allow_reuse=True)(convert_object_to_scalar)
    _publication_to_scalar = validator('publications', allow_reuse=True)(convert_objects_to_scalars)
    #_qualifiers_to_scalar = validator('qualifiers', allow_reuse=True)(convert_objects_to_scalars)

    # validators
    _validate_subject = validator('subject', allow_reuse=True)(field_must_be_curie)
    _validate_predicate = validator('predicate', allow_reuse=True)(field_must_be_curie)
    _validate_object = validator('object', allow_reuse=True)(field_must_be_curie)
    _validate_qualifiers = validator('qualifiers', allow_reuse=True)(list_field_are_curies)
    _validate_publications = validator('publications', allow_reuse=True)(list_field_are_curies)




@dataclass
class GeneToGeneAssociation(Association):
    """
    abstract parent class for different kinds of gene-gene or gene product to gene product
    relationships. Includes homology and interaction.
    """
    _label: ClassVar[str] = 'GeneToGeneAssociation'
    category: ClassVar[List[str]] = ['Association', 'GeneToGeneAssociation']


@dataclass
class PairwiseGeneToGeneInteraction(GeneToGeneAssociation):
    """
    An interaction between two genes or two gene products. May be physical (e.g. protein binding)
    or genetic (between genes). May be symmetric (e.g. protein interaction) or directed (e.g. phosphorylation)
    """
    _label: ClassVar[str] = 'PairwiseGeneToGeneInteraction'

    category: ClassVar[List[str]] = [
        'Association',
        'GeneToGeneAssociation',
        'PairwiseGeneToGeneInteraction',
    ]
