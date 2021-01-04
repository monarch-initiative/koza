from dataclasses import dataclass, field
from typing import Optional, List, Union, Dict, ClassVar, Any

from ..validator import is_valid_curie


@dataclass
class NodeOrEdge:
    """
    Base class for all nodes and edges (associations)

    Note that this is not officially in the biolink model and is a
    convenience class for validating identifiers staying DRY

    Note that only required fields can go here, for now this is only
    ID, which we require to be a curie formatted string
    """

    id: str

    def __post_init__(self):
        if not is_valid_curie(self.id):
            raise ValueError(f"{self.id} is not a curie")


@dataclass
class ThingWithTaxon:
    """
    A mixin that can be used on any entity that can be taxonomically classified.
    This includes individual organisms; genes, their products and other molecular
    entities; body parts; biological processes
    """
    in_taxon: List[str] = field(default_factory=list)

    def __post_init__(self):
        for taxon in self.in_taxon:
            if not is_valid_curie(taxon, ['NCBITaxon']):
                raise ValueError(f"{taxon} is not a curie or not prefixed with NCBITaxon")



@dataclass
class Agent(NodeOrEdge):
    """
    person, group, organization or project that provides a piece of information
    (i.e. a knowledge association)
    """
    _label: ClassVar[str] = 'Agent'

    category: List[str] = field(default_factory=lambda : ['Agent'])
    name: str = None
    affiliation: List[str] = field(default_factory=list)
    address: str = None


@dataclass
class NamedThing(NodeOrEdge):
    """
    Root Biolink Model class for all things and informational relationships,
    real or imagined.
    """
    _label: ClassVar[str] = 'NamedThing'

    category: List[str] = field(default_factory=lambda : ['NamedThing'])
    name: str = None
    iri: str = None
    type: str = None
    description: str = None
    source: str = None
    provided_by: List[Union[str, Agent]] = field(default_factory=list)


@dataclass
class BiologicalEntity(NamedThing):
    _label: ClassVar[str] = 'BiologicalEntity'

    category: List[str] = field(default_factory=lambda: ['NamedThing', 'BiologicalEntity'])


@dataclass
class MolecularEntity(ThingWithTaxon, BiologicalEntity):
    """
    A gene, gene product, small molecule or macromolecule (including protein complex)
    """
    _label: ClassVar[str] = 'MolecularEntity'

    category: List[str] = field(
        default_factory=lambda: [
            'NamedThing',
            'BiologicalEntity',
            'MolecularEntity',
        ]
    )



@dataclass
class GenomicEntity(MolecularEntity):
    _label: ClassVar[str] = 'GenomicEntity'

    category: List[str] = field(
        default_factory=lambda: [
            'NamedThing',
            'BiologicalEntity',
            'MolecularEntity',
            'GenomicEntity',
        ]
    )

    has_biological_sequence: Optional[str] = None


@dataclass
class MacromolecularMachine(GenomicEntity):
    """
    A union of gene, gene product, and macromolecular complex. These are the basic
    units of function in a cell. They either carry out individual biological
    activities, or they encode molecules which do this.
    """

    _label: ClassVar[str] = 'MacromolecularMachine'

    category: List[str] = field(
        default_factory=lambda: [
            'NamedThing',
            'BiologicalEntity',
            'MolecularEntity',
            'GenomicEntity',
            'MacromolecularMachine',
        ]
    )



@dataclass
class GeneOrGeneProduct(MacromolecularMachine):
    """
    a union of genes or gene products. Frequently an identifier for one will be used
    as proxy for another
    """
    _label: ClassVar[str] = 'GeneOrGeneProduct'

    category: List[str] = field(
        default_factory=lambda: [
            'NamedThing',
            'BiologicalEntity',
            'MolecularEntity',
            'GenomicEntity',
            'MacromolecularMachine',
            'GeneOrGeneProduct',
        ]
    )


@dataclass
class Gene(GeneOrGeneProduct):
    _label: ClassVar[str] = 'Gene'

    category: List[str] = field(
        default_factory=lambda: [
            'NamedThing',
            'BiologicalEntity',
            'MolecularEntity',
            'GenomicEntity',
            'MacromolecularMachine',
            'GeneOrGeneProduct',
            'Gene',
        ]
    )

    symbol: str = None
    synonym: List[str] = field(default_factory=list)
    xref: List[str] = field(default_factory=list)
