"""
Biolink Model Dataclasses + Pydantic validators

Longer term generate this from Biolink model yaml
https://github.com/biolink/biolink-model/blob/master/biolink-model.yaml

"""

from dataclasses import field
from pydantic.dataclasses import dataclass
from pydantic import validator
from typing import Optional, List, Union, Dict, ClassVar, Any

from bioweave.validator import *

# Type alias for use in serializers
Curie = str


@dataclass
class ThingWithTaxon:
    """
    A mixin that can be used on any entity that can be taxonomically classified.
    This includes individual organisms; genes, their products and other molecular
    entities; body parts; biological processes
    """
    in_taxon: List[Curie] = field(default_factory=list)

    # validators
    _validate_in_taxon = validator('in_taxon', allow_reuse=True)(field_must_be_curie)
    _validate_prefix = validator('in_taxon', allow_reuse=True)(valid_taxon)


@dataclass
class Entity:
    """
    Root Biolink Model class for all things and informational relationships, real or imagined
    """
    _label: ClassVar[str] = 'Entity'
    category: ClassVar[List[str]] = []

    id: Curie = None
    name: str = ''
    iri: str = None
    type: str = None
    description: str = None
    source: str = None
    provided_by: Union[str, List[str]] = field(default_factory=list)

    # validators
    _validate_id = validator('id', allow_reuse=True)(field_must_be_curie)

    # converters
    _validate_provided_by = validator('provided_by', allow_reuse=True)(convert_object_to_scalar)


@dataclass
class NamedThing(Entity):
    """
    Root Biolink Model class for all things and informational relationships, real or imagined
    """
    _label: ClassVar[str] = 'NamedThing'
    category: ClassVar[List[str]] = ['NamedThing']


@dataclass
class Agent(Entity):
    """
    person, group, organization or project that provides a piece of information
    (i.e. a knowledge association)
    """
    _label: ClassVar[str] = 'Agent'
    category: ClassVar[List[str]] = ['Agent']

    affiliation: List[str] = field(default_factory=list)
    address: str = None


@dataclass
class BiologicalEntity(NamedThing):
    _label: ClassVar[str] = 'BiologicalEntity'
    category: ClassVar[List[str]] = ['NamedThing', 'BiologicalEntity']


@dataclass
class MolecularEntity(ThingWithTaxon, BiologicalEntity):
    """
    A gene, gene product, small molecule or macromolecule (including protein complex)
    """
    _label: ClassVar[str] = 'MolecularEntity'
    category: ClassVar[List[str]] = ['NamedThing', 'BiologicalEntity', 'MolecularEntity']


@dataclass
class GenomicEntity(MolecularEntity):
    _label: ClassVar[str] = 'GenomicEntity'

    category: ClassVar[List[str]] = [
        'NamedThing',
        'BiologicalEntity',
        'MolecularEntity',
        'GenomicEntity',
    ]

    has_biological_sequence: Optional[str] = None


@dataclass
class MacromolecularMachine(GenomicEntity):
    """
    A union of gene, gene product, and macromolecular complex. These are the basic
    units of function in a cell. They either carry out individual biological
    activities, or they encode molecules which do this.
    """

    _label: ClassVar[str] = 'MacromolecularMachine'
    category: ClassVar[List[str]] = [
        'NamedThing',
        'BiologicalEntity',
        'MolecularEntity',
        'GenomicEntity',
        'MacromolecularMachine',
    ]


@dataclass
class GeneOrGeneProduct(MacromolecularMachine):
    """
    a union of genes or gene products. Frequently an identifier for one will be used
    as proxy for another
    """
    _label: ClassVar[str] = 'GeneOrGeneProduct'

    category: ClassVar[List[str]] = [
        'NamedThing',
        'BiologicalEntity',
        'MolecularEntity',
        'GenomicEntity',
        'MacromolecularMachine',
        'GeneOrGeneProduct',
    ]


@dataclass
class Gene(GeneOrGeneProduct):
    _label: ClassVar[str] = 'Gene'

    category: ClassVar[List[str]] = [
        'NamedThing',
        'BiologicalEntity',
        'MolecularEntity',
        'GenomicEntity',
        'MacromolecularMachine',
        'GeneOrGeneProduct',
        'Gene',
    ]

    symbol: str = None
    synonym: List[str] = field(default_factory=list)
    xref: List[str] = field(default_factory=list)
