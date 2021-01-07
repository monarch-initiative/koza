"""
Biolink Model Dataclasses + Pydantic validators

Longer term generate this from Biolink model yaml
https://github.com/biolink/biolink-model/blob/master/biolink-model.yaml

"""

from dataclasses import field
from pydantic.dataclasses import dataclass
from pydantic import validator
from typing import List, ClassVar

from bioweave.validator import is_valid_curie
from .named_thing import Entity

# Type alias for use in serializers
Curie = str


@dataclass
class Association(Entity):
    """
    A typed association between two entities, supported by evidence
    """

    _label: ClassVar[str] = 'Association'
    category: ClassVar[List[str]] = ['Association']

    subject: Curie = None
    predicate: Curie = None
    object: Curie = None
    relation: str = None
    negated: bool = False
    qualifiers: List[Curie] = field(default_factory=list)
    publications: List[Curie] = field(default_factory=list)
    type: Curie = 'rdf:Statement'

    @validator('subject')
    def subject_must_be_curie(cls, subject):
        if not is_valid_curie(subject):
            raise ValueError(f"{subject} is not a curie")
        return subject

    @validator('object')
    def object_must_be_curie(cls, obj):
        if not is_valid_curie(obj):
            raise ValueError(f"{obj} is not a curie")
        return obj

    @validator('predicate')
    def predicate_must_be_curie(cls, predicate):
        if not is_valid_curie(predicate):
            raise ValueError(f"{predicate} is not a curie")
        return predicate

    @validator('qualifiers')
    def qualifier_must_be_curie(cls, qualifiers):
        for qualifier in qualifiers:
            if not is_valid_curie(qualifier):
                raise ValueError(f"{qualifier} is not a curie")
        return qualifiers

    @validator('publications')
    def publication_validator(cls, publications):
        valid_prefix = [
            'DOI',
            'GeneReviews',
            'ISBN',
            'ISBN-10',
            'ISBN-13',
            'J',
            'PMID',
            'PMCID',
            'AspGD_REF',
            'AQTLPub',
            'GO_REF',
            'PAINT-REF',
            'OMIM',
            'ORPHA',
            'DECIPHER',
            'FlyBase',
        ]
        for pub in publications:
            if not is_valid_curie(pub, valid_prefix):
                raise ValueError(f"{pub} is not a curie or not prefixed with {valid_prefix}")
        return publications

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
