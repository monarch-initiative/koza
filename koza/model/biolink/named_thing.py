"""
Biolink Model Dataclasses + Pydantic validators

Longer term generate this from Biolink model yaml
https://github.com/biolink/biolink-model/blob/master/biolink-model.yaml

"""

from dataclasses import field
from typing import ClassVar, Optional

from pydantic.dataclasses import dataclass

from koza.validator.model_validator import *

from ..config.pydantic_config import PydanticConfig
from ..curie import Curie


@dataclass(config=PydanticConfig)
class ThingWithTaxon:
    """
    A mixin that can be used on any entity that can be taxonomically classified.
    This includes individual organisms; genes, their products and other molecular
    entities; body parts; biological processes
    """

    in_taxon: List[Curie] = field(default_factory=list)

    _validate_prefix = valid_taxon("in_taxon")


@dataclass(config=PydanticConfig)
class NamedThing(Entity):
    """
    Root Biolink Model class for all things and informational relationships, real or imagined
    """

    _category: ClassVar[str] = 'NamedThing'


@dataclass(config=PydanticConfig)
class Agent(Entity):
    """
    person, group, organization or project that provides a piece of information
    (i.e. a knowledge association)
    """

    _category: ClassVar[str] = 'Agent'

    affiliation: List[str] = field(default_factory=list)
    address: str = None


@dataclass(config=PydanticConfig)
class BiologicalEntity(NamedThing):
    _category: ClassVar[str] = 'BiologicalEntity'


@dataclass(config=PydanticConfig)
class MolecularEntity(ThingWithTaxon, BiologicalEntity):
    """
    A gene, gene product, small molecule or macromolecule (including protein complex)
    """

    _category: ClassVar[str] = 'MolecularEntity'


@dataclass(config=PydanticConfig)
class GenomicEntity(MolecularEntity):

    _category: ClassVar[str] = 'GenomicEntity'

    has_biological_sequence: Optional[str] = None


@dataclass(config=PydanticConfig)
class MacromolecularMachine(GenomicEntity):
    """
    A union of gene, gene product, and macromolecular complex. These are the basic
    units of function in a cell. They either carry out individual biological
    activities, or they encode molecules which do this.
    """

    _category: ClassVar[str] = 'MacromolecularMachine'


@dataclass(config=PydanticConfig)
class GeneOrGeneProduct(MacromolecularMachine):
    """
    a union of genes or gene products. Frequently an identifier for one will be used
    as proxy for another
    """

    _category: ClassVar[str] = 'GeneOrGeneProduct'


@dataclass(config=PydanticConfig)
class Gene(GeneOrGeneProduct):
    _category: ClassVar[str] = 'Gene'

    symbol: str = None
    synonym: List[str] = field(default_factory=list)
    xref: List[str] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class Protein(Gene):
    _category: ClassVar[str] = 'Protein'


@dataclass(config=PydanticConfig)
class InformationContentEntity(NamedThing):
    """
    a piece of information that typically describes some topic of discourse or is used as support.
    """

    _category: ClassVar[str] = 'InformationContentEntity'

    license: str = None
    rights: str = None
    format: str = None
    creation_date: str = None


@dataclass(config=PydanticConfig)
class Publication(InformationContentEntity):
    """
    Any published piece of information. Can refer to a whole publication, its encompassing publication (i.e. journal
    or book) or to a part of a publication, if of significant knowledge scope (e.g. a figure, figure legend, or
    section highlighted by NLP). The scope is intended to be general and include information published on the web, as
    well as printed materials, either directly or in one of the Publication Biolink category subclasses.
    """

    _category: ClassVar[str] = 'Publication'

    authors: List[str] = field(default_factory=list)
    pages: List[str] = field(default_factory=list)
    summary: str = None
    keywords: List[str] = field(default_factory=list)
    mesh_terms: List[Curie] = field(default_factory=list)
