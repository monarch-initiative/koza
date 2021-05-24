# Auto generated from biolink-model.yaml by pydanticgen.py version: 0.9.0
# Generation date: 2021-05-24 16:39
# Schema: Biolink-Model
#
# id: https://w3id.org/biolink/biolink-model
# description: Entity and association taxonomy and datamodel for life-sciences data
# license: https://creativecommons.org/publicdomain/zero/1.0/

import datetime
import inspect
from collections import namedtuple
from dataclasses import field
from typing import ClassVar, List, Optional, Union

from pydantic.dataclasses import dataclass

from koza.model.config.pydantic_config import PydanticConfig
from koza.model.curie import Curie

metamodel_version = "1.7.0"

# Type Aliases
Unit = Union[int, float]
LabelType = str
NarrativeText = str
XSDDate = datetime.date
TimeType = datetime.time
SymbolType = str
FrequencyValue = str
PercentageFrequencyValue = float
BiologicalSequence = str
Quotient = float

# Classes


class OntologyClass:
    """
    a concept or class in an ontology, vocabulary or thesaurus. Note that nodes in a biolink compatible KG can be
    considered both instances of biolink classes, and OWL classes in their own right. In general you should not need
    to use this class directly. Instead, use the appropriate biolink class. For example, for the GO concept of
    endocytosis (GO:0006897), use bl:BiologicalProcess as the type.
    """


class Annotation:
    """
    Biolink Model root class for entity annotations.
    """


@dataclass(config=PydanticConfig)
class QuantityValue(Annotation):
    """
    A value of an attribute that is quantitative and measurable, expressed as a combination of a unit and a numeric
    value
    """

    _category: ClassVar[str] = "QuantityValue"

    has_unit: Optional[Union[str, Unit]] = None
    has_numeric_value: Optional[float] = None


@dataclass(config=PydanticConfig)
class Attribute(Annotation, OntologyClass):
    """
    A property or characteristic of an entity. For example, an apple may have properties such as color, shape, age,
    crispiness. An environmental sample may have attributes such as depth, lat, long, material.
    """

    _category: ClassVar[str] = "Attribute"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]

    has_attribute_type: Union[str, OntologyClass] = None
    name: Optional[Union[str, LabelType]] = None
    has_quantitative_value: Optional[
        Union[Union[str, QuantityValue], List[Union[str, QuantityValue]]]
    ] = field(default_factory=list)
    has_qualitative_value: Optional[Union[str, Curie]] = None
    iri: Optional[Union[str, Curie]] = None
    source: Optional[Union[str, LabelType]] = None


@dataclass(config=PydanticConfig)
class BiologicalSex(Attribute):

    _category: ClassVar[str] = "BiologicalSex"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]

    has_attribute_type: Union[str, OntologyClass] = None


@dataclass(config=PydanticConfig)
class PhenotypicSex(BiologicalSex):
    """
    An attribute corresponding to the phenotypic sex of the individual, based upon the reproductive organs present.
    """

    _category: ClassVar[str] = "PhenotypicSex"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]

    has_attribute_type: Union[str, OntologyClass] = None


@dataclass(config=PydanticConfig)
class GenotypicSex(BiologicalSex):
    """
    An attribute corresponding to the genotypic sex of the individual, based upon genotypic composition of sex
    chromosomes.
    """

    _category: ClassVar[str] = "GenotypicSex"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]

    has_attribute_type: Union[str, OntologyClass] = None


@dataclass(config=PydanticConfig)
class SeverityValue(Attribute):
    """
    describes the severity of a phenotypic feature or disease
    """

    _category: ClassVar[str] = "SeverityValue"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]

    has_attribute_type: Union[str, OntologyClass] = None


class RelationshipQuantifier:

    pass


class SensitivityQuantifier(RelationshipQuantifier):

    pass


class SpecificityQuantifier(RelationshipQuantifier):

    pass


class PathognomonicityQuantifier(SpecificityQuantifier):
    """
    A relationship quantifier between a variant or symptom and a disease, which is high when the presence of the
    feature implies the existence of the disease
    """


@dataclass(config=PydanticConfig)
class FrequencyQuantifier(RelationshipQuantifier):

    has_count: Optional[int] = None
    has_total: Optional[int] = None
    has_quotient: Optional[float] = None
    has_percentage: Optional[float] = None


class ChemicalOrDrugOrTreatment:

    pass


@dataclass(config=PydanticConfig)
class Entity:
    """
    Root Biolink Model class for all things and informational relationships, real or imagined.
    """

    _required_attributes: ClassVar[List[str]] = ["id"]

    id: Union[str, Curie] = None
    iri: Optional[Union[str, Curie]] = None
    category: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(
        default_factory=list
    )
    type: Optional[str] = None
    name: Optional[Union[str, LabelType]] = None
    description: Optional[Union[str, NarrativeText]] = None
    source: Optional[Union[str, LabelType]] = None
    provided_by: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(
        default_factory=list
    )
    has_attribute: Optional[Union[Union[str, Attribute], List[Union[str, Attribute]]]] = field(
        default_factory=list
    )

    def __post_init__(self):
        # Initialize default categories if not set
        # by traversing the MRO chain
        if not self.category:
            self.category = list(
                {
                    super_class._category
                    for super_class in inspect.getmro(type(self))
                    if hasattr(super_class, '_category')
                }
            )


@dataclass(config=PydanticConfig)
class NamedThing(Entity):
    """
    a databased entity or concept/class
    """

    _category: ClassVar[str] = "NamedThing"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


class RelationshipType(OntologyClass):
    """
    An OWL property used as an edge label
    """

    _category: ClassVar[str] = "RelationshipType"


class GeneOntologyClass(OntologyClass):
    """
    an ontology class that describes a functional aspect of a gene, gene prodoct or complex
    """


class UnclassifiedOntologyClass(OntologyClass):
    """
    this is used for nodes that are taken from an ontology but are not typed using an existing biolink class
    """


class TaxonomicRank(OntologyClass):
    """
    A descriptor for the rank within a taxonomic classification. Example instance: TAXRANK:0000017 (kingdom)
    """

    _category: ClassVar[str] = "TaxonomicRank"


@dataclass(config=PydanticConfig)
class OrganismTaxon(NamedThing):
    """
    A classification of a set of organisms. Example instances: NCBITaxon:9606 (Homo sapiens), NCBITaxon:2 (Bacteria).
    Can also be used to represent strains or subspecies.
    """

    _category: ClassVar[str] = "OrganismTaxon"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    has_taxonomic_rank: Optional[Union[str, TaxonomicRank]] = None
    subclass_of: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(
        default_factory=list
    )


@dataclass(config=PydanticConfig)
class AdministrativeEntity(NamedThing):

    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Agent(AdministrativeEntity):
    """
    person, group, organization or project that provides a piece of information (i.e. a knowledge association)
    """

    _category: ClassVar[str] = "Agent"
    _required_attributes: ClassVar[List[str]] = ["category", "id"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    affiliation: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(
        default_factory=list
    )
    address: Optional[str] = None
    name: Optional[Union[str, LabelType]] = None


@dataclass(config=PydanticConfig)
class InformationContentEntity(NamedThing):
    """
    a piece of information that typically describes some topic of discourse or is used as support.
    """

    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    license: Optional[str] = None
    rights: Optional[str] = None
    format: Optional[str] = None
    creation_date: Optional[Union[str, XSDDate]] = None


@dataclass(config=PydanticConfig)
class Dataset(InformationContentEntity):
    """
    an item that refers to a collection of data from a data source.
    """

    _category: ClassVar[str] = "Dataset"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class DatasetDistribution(InformationContentEntity):
    """
    an item that holds distribution level information about a dataset.
    """

    _category: ClassVar[str] = "DatasetDistribution"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    distribution_download_url: Optional[str] = None


@dataclass(config=PydanticConfig)
class DatasetVersion(InformationContentEntity):
    """
    an item that holds version level information about a dataset.
    """

    _category: ClassVar[str] = "DatasetVersion"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    has_dataset: Optional[Union[str, Curie, Dataset]] = None
    ingest_date: Optional[str] = None
    has_distribution: Optional[Union[str, Curie, DatasetDistribution]] = None


@dataclass(config=PydanticConfig)
class DatasetSummary(InformationContentEntity):
    """
    an item that holds summary level information about a dataset.
    """

    _category: ClassVar[str] = "DatasetSummary"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    source_web_page: Optional[str] = None
    source_logo: Optional[str] = None


@dataclass(config=PydanticConfig)
class ConfidenceLevel(InformationContentEntity):
    """
    Level of confidence in a statement
    """

    _category: ClassVar[str] = "ConfidenceLevel"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class EvidenceType(InformationContentEntity):
    """
    Class of evidence that supports an association
    """

    _category: ClassVar[str] = "EvidenceType"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Publication(InformationContentEntity):
    """
    Any published piece of information. Can refer to a whole publication, its encompassing publication (i.e. journal
    or book) or to a part of a publication, if of significant knowledge scope (e.g. a figure, figure legend, or
    section highlighted by NLP). The scope is intended to be general and include information published on the web, as
    well as printed materials, either directly or in one of the Publication Biolink category subclasses.
    """

    _category: ClassVar[str] = "Publication"
    _required_attributes: ClassVar[List[str]] = ["category", "id", "type"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    type: str = None
    authors: Optional[Union[str, List[str]]] = field(default_factory=list)
    pages: Optional[Union[str, List[str]]] = field(default_factory=list)
    summary: Optional[str] = None
    keywords: Optional[Union[str, List[str]]] = field(default_factory=list)
    mesh_terms: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(
        default_factory=list
    )
    xref: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(default_factory=list)
    name: Optional[Union[str, LabelType]] = None


@dataclass(config=PydanticConfig)
class Book(Publication):
    """
    This class may rarely be instantiated except if use cases of a given knowledge graph support its utility.
    """

    _category: ClassVar[str] = "Book"
    _required_attributes: ClassVar[List[str]] = ["category", "id", "type"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    type: str = None


@dataclass(config=PydanticConfig)
class BookChapter(Publication):

    _category: ClassVar[str] = "BookChapter"
    _required_attributes: ClassVar[List[str]] = ["category", "id", "type", "published_in"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    type: str = None
    published_in: Union[str, Curie] = None
    volume: Optional[str] = None
    chapter: Optional[str] = None


@dataclass(config=PydanticConfig)
class Serial(Publication):
    """
    This class may rarely be instantiated except if use cases of a given knowledge graph support its utility.
    """

    _category: ClassVar[str] = "Serial"
    _required_attributes: ClassVar[List[str]] = ["category", "id", "type"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    type: str = None
    iso_abbreviation: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None


@dataclass(config=PydanticConfig)
class Article(Publication):

    _category: ClassVar[str] = "Article"
    _required_attributes: ClassVar[List[str]] = ["category", "id", "type", "published_in"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    type: str = None
    published_in: Union[str, Curie] = None
    iso_abbreviation: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None


class PhysicalEssenceOrOccurrent:
    """
    Either a physical or processual entity.
    """


class PhysicalEssence(PhysicalEssenceOrOccurrent):
    """
    Semantic mixin concept.  Pertains to entities that have physical properties such as mass, volume, or charge.
    """


@dataclass(config=PydanticConfig)
class PhysicalEntity(NamedThing, PhysicalEssence):
    """
    An entity that has material reality (a.k.a. physical essence).
    """

    _category: ClassVar[str] = "PhysicalEntity"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


class Occurrent(PhysicalEssenceOrOccurrent):
    """
    A processual entity.
    """


class ActivityAndBehavior(Occurrent):
    """
    Activity or behavior of any independent integral living, organization or mechanical actor in the world
    """


@dataclass(config=PydanticConfig)
class Activity(NamedThing, ActivityAndBehavior):
    """
    An activity is something that occurs over a period of time and acts upon or with entities; it may include
    consuming, processing, transforming, modifying, relocating, using, or generating entities.
    """

    _category: ClassVar[str] = "Activity"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Procedure(NamedThing, ActivityAndBehavior):
    """
    A series of actions conducted in a certain order or manner
    """

    _category: ClassVar[str] = "Procedure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Phenomenon(NamedThing, Occurrent):
    """
    a fact or situation that is observed to exist or happen, especially one whose cause or explanation is in question
    """

    _category: ClassVar[str] = "Phenomenon"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Device(NamedThing):
    """
    A thing made or adapted for a particular purpose, especially a piece of mechanical or electronic equipment
    """

    _category: ClassVar[str] = "Device"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


class SubjectOfInvestigation:
    """
    An entity that has the role of being studied in an investigation, study, or experiment
    """


@dataclass(config=PydanticConfig)
class MaterialSample(PhysicalEntity, SubjectOfInvestigation):
    """
    A sample is a limited quantity of something (e.g. an individual or set of individuals from a population, or a
    portion of a substance) to be used for testing, analysis, inspection, investigation, demonstration, or trial use.
    [SIO]
    """

    _category: ClassVar[str] = "MaterialSample"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class PlanetaryEntity(NamedThing):
    """
    Any entity or process that exists at the level of the whole planet
    """

    _category: ClassVar[str] = "PlanetaryEntity"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class EnvironmentalProcess(PlanetaryEntity, Occurrent):

    _category: ClassVar[str] = "EnvironmentalProcess"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class EnvironmentalFeature(PlanetaryEntity):

    _category: ClassVar[str] = "EnvironmentalFeature"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class GeographicLocation(PlanetaryEntity):
    """
    a location that can be described in lat/long coordinates
    """

    _category: ClassVar[str] = "GeographicLocation"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass(config=PydanticConfig)
class GeographicLocationAtTime(GeographicLocation):
    """
    a location that can be described in lat/long coordinates, for a particular time
    """

    _category: ClassVar[str] = "GeographicLocationAtTime"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    timepoint: Optional[Union[str, TimeType]] = None


@dataclass(config=PydanticConfig)
class BiologicalEntity(NamedThing):

    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class ThingWithTaxon:
    """
    A mixin that can be used on any entity that can be taxonomically classified. This includes individual organisms;
    genes, their products and other molecular entities; body parts; biological processes
    """

    in_taxon: Optional[
        Union[Union[str, Curie, OrganismTaxon], List[Union[str, Curie, OrganismTaxon]]]
    ] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class MolecularEntity(BiologicalEntity, ThingWithTaxon, PhysicalEssence, OntologyClass):
    """
    A gene, gene product, small molecule or macromolecule (including protein complex)"
    """

    _category: ClassVar[str] = "MolecularEntity"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    in_taxon: Optional[
        Union[Union[str, Curie, OrganismTaxon], List[Union[str, Curie, OrganismTaxon]]]
    ] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class BiologicalProcessOrActivity(BiologicalEntity, Occurrent, OntologyClass):
    """
    Either an individual molecular activity, or a collection of causally connected molecular activities in a
    biological system.
    """

    _category: ClassVar[str] = "BiologicalProcessOrActivity"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    has_input: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(
        default_factory=list
    )
    has_output: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(
        default_factory=list
    )
    enabled_by: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(
        default_factory=list
    )


@dataclass(config=PydanticConfig)
class MolecularActivity(BiologicalProcessOrActivity, Occurrent, OntologyClass):
    """
    An execution of a molecular function carried out by a gene product or macromolecular complex.
    """

    _category: ClassVar[str] = "MolecularActivity"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    has_input: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(
        default_factory=list
    )
    has_output: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(
        default_factory=list
    )
    enabled_by: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(
        default_factory=list
    )


@dataclass(config=PydanticConfig)
class BiologicalProcess(BiologicalProcessOrActivity, Occurrent, OntologyClass):
    """
    One or more causally connected executions of molecular functions
    """

    _category: ClassVar[str] = "BiologicalProcess"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Pathway(BiologicalProcess, OntologyClass):

    _category: ClassVar[str] = "Pathway"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class PhysiologicalProcess(BiologicalProcess, OntologyClass):

    _category: ClassVar[str] = "PhysiologicalProcess"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Behavior(BiologicalProcess, OntologyClass):

    _category: ClassVar[str] = "Behavior"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Death(BiologicalProcess):

    _category: ClassVar[str] = "Death"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Mixture:
    """
    The physical combination of two or more molecular entities in which the identities are retained and are mixed in
    the form of solutions, suspensions and colloids.
    """

    has_constituent: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(
        default_factory=list
    )


@dataclass(config=PydanticConfig)
class ChemicalSubstance(MolecularEntity, OntologyClass):
    """
    May be a chemical entity or a formulation with a chemical entity as active ingredient, or a complex material with
    multiple chemical entities as part
    """

    _category: ClassVar[str] = "ChemicalSubstance"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    is_metabolite: Optional[bool] = None


@dataclass(config=PydanticConfig)
class Carbohydrate(ChemicalSubstance):

    _category: ClassVar[str] = "Carbohydrate"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class ProcessedMaterial(ChemicalSubstance, Mixture, OntologyClass):
    """
    A chemical substance (often a mixture) processed for consumption for nutritional, medical or technical use.
    """

    _category: ClassVar[str] = "ProcessedMaterial"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    has_constituent: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(
        default_factory=list
    )


@dataclass(config=PydanticConfig)
class Drug(MolecularEntity, Mixture, ChemicalOrDrugOrTreatment, OntologyClass):
    """
    A substance intended for use in the diagnosis, cure, mitigation, treatment, or prevention of disease
    """

    _category: ClassVar[str] = "Drug"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    has_constituent: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(
        default_factory=list
    )


@dataclass(config=PydanticConfig)
class FoodComponent(ChemicalSubstance):

    _category: ClassVar[str] = "FoodComponent"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class EnvironmentalFoodContaminant(ChemicalSubstance):

    _category: ClassVar[str] = "EnvironmentalFoodContaminant"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class FoodAdditive(ChemicalSubstance):

    _category: ClassVar[str] = "FoodAdditive"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Nutrient(ChemicalSubstance):

    _category: ClassVar[str] = "Nutrient"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Macronutrient(Nutrient):

    _category: ClassVar[str] = "Macronutrient"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Micronutrient(Nutrient):

    _category: ClassVar[str] = "Micronutrient"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Vitamin(Micronutrient):

    _category: ClassVar[str] = "Vitamin"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Food(MolecularEntity, Mixture):
    """
    A substance consumed by a living organism as a source of nutrition
    """

    _category: ClassVar[str] = "Food"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    has_constituent: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(
        default_factory=list
    )


@dataclass(config=PydanticConfig)
class Metabolite(ChemicalSubstance):
    """
    Any intermediate or product resulting from metabolism. Includes primary and secondary metabolites.
    """

    _category: ClassVar[str] = "Metabolite"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class OrganismAttribute(Attribute):
    """
    describes a characteristic of an organismal entity.
    """

    _category: ClassVar[str] = "OrganismAttribute"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]

    has_attribute_type: Union[str, OntologyClass] = None


@dataclass(config=PydanticConfig)
class PhenotypicQuality(OrganismAttribute):
    """
    A property of a phenotype
    """

    _category: ClassVar[str] = "PhenotypicQuality"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]

    has_attribute_type: Union[str, OntologyClass] = None


@dataclass(config=PydanticConfig)
class Inheritance(OrganismAttribute):
    """
    The pattern or 'mode' in which a particular genetic trait or disorder is passed from one generation to the next,
    e.g. autosomal dominant, autosomal recessive, etc.
    """

    _category: ClassVar[str] = "Inheritance"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]

    has_attribute_type: Union[str, OntologyClass] = None


@dataclass(config=PydanticConfig)
class OrganismalEntity(BiologicalEntity):
    """
    A named entity that is either a part of an organism, a whole organism, population or clade of organisms, excluding
    molecular entities
    """

    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    has_attribute: Optional[Union[Union[str, Attribute], List[Union[str, Attribute]]]] = field(
        default_factory=list
    )


@dataclass(config=PydanticConfig)
class LifeStage(OrganismalEntity, ThingWithTaxon):
    """
    A stage of development or growth of an organism, including post-natal adult stages
    """

    _category: ClassVar[str] = "LifeStage"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    in_taxon: Optional[
        Union[Union[str, Curie, OrganismTaxon], List[Union[str, Curie, OrganismTaxon]]]
    ] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class IndividualOrganism(OrganismalEntity, ThingWithTaxon):
    """
    An instance of an organism. For example, Richard Nixon, Charles Darwin, my pet cat. Example ID:
    ORCID:0000-0002-5355-2576
    """

    _category: ClassVar[str] = "IndividualOrganism"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    in_taxon: Optional[
        Union[Union[str, Curie, OrganismTaxon], List[Union[str, Curie, OrganismTaxon]]]
    ] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class PopulationOfIndividualOrganisms(OrganismalEntity, ThingWithTaxon):
    """
    A collection of individuals from the same taxonomic class distinguished by one or more characteristics.
    Characteristics can include, but are not limited to, shared geographic location, genetics, phenotypes [Alliance
    for Genome Resources]
    """

    _category: ClassVar[str] = "PopulationOfIndividualOrganisms"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    in_taxon: Optional[
        Union[Union[str, Curie, OrganismTaxon], List[Union[str, Curie, OrganismTaxon]]]
    ] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class StudyPopulation(PopulationOfIndividualOrganisms):
    """
    A group of people banded together or treated as a group as participants in a research study.
    """

    _category: ClassVar[str] = "StudyPopulation"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class DiseaseOrPhenotypicFeature(BiologicalEntity, ThingWithTaxon):
    """
    Either one of a disease or an individual phenotypic feature. Some knowledge resources such as Monarch treat these
    as distinct, others such as MESH conflate.
    """

    _category: ClassVar[str] = "DiseaseOrPhenotypicFeature"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    in_taxon: Optional[
        Union[Union[str, Curie, OrganismTaxon], List[Union[str, Curie, OrganismTaxon]]]
    ] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class Disease(DiseaseOrPhenotypicFeature):

    _category: ClassVar[str] = "Disease"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class PhenotypicFeature(DiseaseOrPhenotypicFeature):

    _category: ClassVar[str] = "PhenotypicFeature"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class BehavioralFeature(PhenotypicFeature):
    """
    A phenotypic feature which is behavioral in nature.
    """

    _category: ClassVar[str] = "BehavioralFeature"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class AnatomicalEntity(OrganismalEntity, ThingWithTaxon, PhysicalEssence):
    """
    A subcellular location, cell type or gross anatomical part
    """

    _category: ClassVar[str] = "AnatomicalEntity"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    in_taxon: Optional[
        Union[Union[str, Curie, OrganismTaxon], List[Union[str, Curie, OrganismTaxon]]]
    ] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class CellularComponent(AnatomicalEntity):
    """
    A location in or around a cell
    """

    _category: ClassVar[str] = "CellularComponent"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Cell(AnatomicalEntity):

    _category: ClassVar[str] = "Cell"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class CellLine(OrganismalEntity):

    _category: ClassVar[str] = "CellLine"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class GrossAnatomicalStructure(AnatomicalEntity):

    _category: ClassVar[str] = "GrossAnatomicalStructure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class MacromolecularMachineMixin:
    """
    A union of gene locus, gene product, and macromolecular complex mixin. These are the basic units of function in a
    cell. They either carry out individual biological activities, or they encode molecules which do this.
    """

    name: Optional[Union[str, SymbolType]] = None


class GeneOrGeneProduct(MacromolecularMachineMixin):
    """
    A union of gene loci or gene products. Frequently an identifier for one will be used as proxy for another
    """


@dataclass(config=PydanticConfig)
class GeneProductMixin(GeneOrGeneProduct):
    """
    The functional molecular product of a single gene locus. Gene products are either proteins or functional RNA
    molecules.
    """

    synonym: Optional[Union[Union[str, LabelType], List[Union[str, LabelType]]]] = field(
        default_factory=list
    )
    xref: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(default_factory=list)


class GeneProductIsoformMixin(GeneProductMixin):
    """
    This is an abstract class that can be mixed in with different kinds of gene products to indicate that the gene
    product is intended to represent a specific isoform rather than a canonical or reference or generic product. The
    designation of canonical or reference may be arbitrary, or it may represent the superclass of all isoforms.
    """


class MacromolecularComplexMixin(MacromolecularMachineMixin):
    """
    A stable assembly of two or more macromolecules, i.e. proteins, nucleic acids, carbohydrates or lipids, in which
    at least one component is a protein and the constituent parts function together.
    """


@dataclass(config=PydanticConfig)
class GenomicEntity(MolecularEntity):
    """
    an entity that can either be directly located on a genome (gene, transcript, exon, regulatory region) or is
    encoded in a genome (protein)
    """

    _category: ClassVar[str] = "GenomicEntity"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    has_biological_sequence: Optional[Union[str, BiologicalSequence]] = None


@dataclass(config=PydanticConfig)
class Gene(GenomicEntity, GeneOrGeneProduct):
    """
    A region (or regions) that includes all of the sequence elements necessary to encode a functional transcript. A
    gene locus may include regulatory regions, transcribed regions and/or other functional sequence regions.
    """

    _category: ClassVar[str] = "Gene"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    symbol: Optional[str] = None
    synonym: Optional[Union[Union[str, LabelType], List[Union[str, LabelType]]]] = field(
        default_factory=list
    )
    xref: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class Genome(GenomicEntity):
    """
    A genome is the sum of genetic material within a cell or virion.
    """

    _category: ClassVar[str] = "Genome"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Exon(GenomicEntity):
    """
    A region of the transcript sequence within a gene which is not removed from the primary RNA transcript by RNA
    splicing.
    """

    _category: ClassVar[str] = "Exon"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Transcript(GenomicEntity):
    """
    An RNA synthesized on a DNA or RNA template by an RNA polymerase.
    """

    _category: ClassVar[str] = "Transcript"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class CodingSequence(GenomicEntity):

    _category: ClassVar[str] = "CodingSequence"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Protein(GenomicEntity, GeneProductMixin):
    """
    A gene product that is composed of a chain of amino acid sequences and is produced by ribosome-mediated
    translation of mRNA
    """

    _category: ClassVar[str] = "Protein"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    synonym: Optional[Union[Union[str, LabelType], List[Union[str, LabelType]]]] = field(
        default_factory=list
    )
    xref: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class ProteinIsoform(Protein, GeneProductIsoformMixin):
    """
    Represents a protein that is a specific isoform of the canonical or reference protein. See
    https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4114032/
    """

    _category: ClassVar[str] = "ProteinIsoform"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class RNAProduct(Transcript, GeneProductMixin):

    _category: ClassVar[str] = "RNAProduct"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    synonym: Optional[Union[Union[str, LabelType], List[Union[str, LabelType]]]] = field(
        default_factory=list
    )
    xref: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class RNAProductIsoform(RNAProduct, GeneProductIsoformMixin):
    """
    Represents a protein that is a specific isoform of the canonical or reference RNA
    """

    _category: ClassVar[str] = "RNAProductIsoform"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class NoncodingRNAProduct(RNAProduct):

    _category: ClassVar[str] = "NoncodingRNAProduct"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class MicroRNA(NoncodingRNAProduct):

    _category: ClassVar[str] = "MicroRNA"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class SiRNA(NoncodingRNAProduct):
    """
    A small RNA molecule that is the product of a longer exogenous or endogenous dsRNA, which is either a bimolecular
    duplex or very long hairpin, processed (via the Dicer pathway) such that numerous siRNAs accumulate from both
    strands of the dsRNA. SRNAs trigger the cleavage of their target molecules.
    """

    _category: ClassVar[str] = "SiRNA"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class GeneGroupingMixin:
    """
    any grouping of multiple genes or gene products
    """

    has_gene_or_gene_product: Optional[
        Union[Union[str, Curie, Gene], List[Union[str, Curie, Gene]]]
    ] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class GeneFamily(MolecularEntity, GeneGroupingMixin):
    """
    any grouping of multiple genes or gene products related by common descent
    """

    _category: ClassVar[str] = "GeneFamily"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    has_gene_or_gene_product: Optional[
        Union[Union[str, Curie, Gene], List[Union[str, Curie, Gene]]]
    ] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class Zygosity(Attribute):

    _category: ClassVar[str] = "Zygosity"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]

    has_attribute_type: Union[str, OntologyClass] = None


@dataclass(config=PydanticConfig)
class Genotype(GenomicEntity):
    """
    An information content entity that describes a genome by specifying the total variation in genomic sequence and/or
    gene expression, relative to some established background
    """

    _category: ClassVar[str] = "Genotype"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    has_zygosity: Optional[Union[str, Zygosity]] = None


@dataclass(config=PydanticConfig)
class Haplotype(GenomicEntity):
    """
    A set of zero or more Alleles on a single instance of a Sequence[VMC]
    """

    _category: ClassVar[str] = "Haplotype"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class SequenceVariant(GenomicEntity):
    """
    An allele that varies in its sequence from what is considered the reference allele at that locus.
    """

    _category: ClassVar[str] = "SequenceVariant"
    _required_attributes: ClassVar[List[str]] = ["category", "id"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    has_gene: Optional[Union[Union[str, Curie, Gene], List[Union[str, Curie, Gene]]]] = field(
        default_factory=list
    )
    has_biological_sequence: Optional[Union[str, BiologicalSequence]] = None


@dataclass(config=PydanticConfig)
class Snv(SequenceVariant):
    """
    SNVs are single nucleotide positions in genomic DNA at which different sequence alternatives exist
    """

    _category: ClassVar[str] = "Snv"
    _required_attributes: ClassVar[List[str]] = ["category", "id"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class ReagentTargetedGene(GenomicEntity):
    """
    A gene altered in its expression level in the context of some experiment as a result of being targeted by
    gene-knockdown reagent(s) such as a morpholino or RNAi.
    """

    _category: ClassVar[str] = "ReagentTargetedGene"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class ClinicalAttribute(Attribute):
    """
    Attributes relating to a clinical manifestation
    """

    _category: ClassVar[str] = "ClinicalAttribute"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]

    has_attribute_type: Union[str, OntologyClass] = None


@dataclass(config=PydanticConfig)
class ClinicalMeasurement(ClinicalAttribute):
    """
    A clinical measurement is a special kind of attribute which results from a laboratory observation from a subject
    individual or sample. Measurements can be connected to their subject by the 'has attribute' slot.
    """

    _category: ClassVar[str] = "ClinicalMeasurement"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]

    has_attribute_type: Union[str, OntologyClass] = None


@dataclass(config=PydanticConfig)
class ClinicalModifier(ClinicalAttribute):
    """
    Used to characterize and specify the phenotypic abnormalities defined in the phenotypic abnormality sub-ontology,
    with respect to severity, laterality, and other aspects
    """

    _category: ClassVar[str] = "ClinicalModifier"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]

    has_attribute_type: Union[str, OntologyClass] = None


@dataclass(config=PydanticConfig)
class ClinicalCourse(ClinicalAttribute):
    """
    The course a disease typically takes from its onset, progression in time, and eventual resolution or death of the
    affected individual
    """

    _category: ClassVar[str] = "ClinicalCourse"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]

    has_attribute_type: Union[str, OntologyClass] = None


@dataclass(config=PydanticConfig)
class Onset(ClinicalCourse):
    """
    The age group in which (disease) symptom manifestations appear
    """

    _category: ClassVar[str] = "Onset"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]

    has_attribute_type: Union[str, OntologyClass] = None


@dataclass(config=PydanticConfig)
class ClinicalEntity(NamedThing):
    """
    Any entity or process that exists in the clinical domain and outside the biological realm. Diseases are placed
    under biological entities
    """

    _category: ClassVar[str] = "ClinicalEntity"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class ClinicalTrial(ClinicalEntity):

    _category: ClassVar[str] = "ClinicalTrial"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class ClinicalIntervention(ClinicalEntity):

    _category: ClassVar[str] = "ClinicalIntervention"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class ClinicalFinding(PhenotypicFeature):
    """
    this category is currently considered broad enough to tag clinical lab measurements and other biological
    attributes taken as 'clinical traits' with some statistical score, for example, a p value in genetic associations.
    """

    _category: ClassVar[str] = "ClinicalFinding"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    has_attribute: Optional[
        Union[Union[str, ClinicalAttribute], List[Union[str, ClinicalAttribute]]]
    ] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class Hospitalization(ClinicalIntervention):

    _category: ClassVar[str] = "Hospitalization"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class SocioeconomicAttribute(Attribute):
    """
    Attributes relating to a socioeconomic manifestation
    """

    _category: ClassVar[str] = "SocioeconomicAttribute"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]

    has_attribute_type: Union[str, OntologyClass] = None


@dataclass(config=PydanticConfig)
class Case(IndividualOrganism):
    """
    An individual (human) organism that has a patient role in some clinical context.
    """

    _category: ClassVar[str] = "Case"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Cohort(StudyPopulation):
    """
    A group of people banded together or treated as a group who share common characteristics. A cohort 'study' is a
    particular form of longitudinal study that samples a cohort, performing a cross-section at intervals through time.
    """

    _category: ClassVar[str] = "Cohort"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class ExposureEvent:
    """
    A (possibly time bounded) incidence of a feature of the environment of an organism that influences one or more
    phenotypic features of that organism, potentially mediated by genes
    """

    timepoint: Optional[Union[str, TimeType]] = None


@dataclass(config=PydanticConfig)
class GenomicBackgroundExposure(GenomicEntity, ExposureEvent, GeneGroupingMixin):
    """
    A genomic background exposure is where an individual's specific genomic background of genes, sequence variants or
    other pre-existing genomic conditions constitute a kind of 'exposure' to the organism, leading to or influencing
    an outcome.
    """

    _category: ClassVar[str] = "GenomicBackgroundExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    timepoint: Optional[Union[str, TimeType]] = None
    has_gene_or_gene_product: Optional[
        Union[Union[str, Curie, Gene], List[Union[str, Curie, Gene]]]
    ] = field(default_factory=list)


class PathologicalEntityMixin:
    """
    A pathological (abnormal) structure or process.
    """


@dataclass(config=PydanticConfig)
class PathologicalProcess(BiologicalProcess, PathologicalEntityMixin):
    """
    A biologic function or a process having an abnormal or deleterious effect at the subcellular, cellular,
    multicellular, or organismal level.
    """

    _category: ClassVar[str] = "PathologicalProcess"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class PathologicalProcessExposure(PathologicalProcess, ExposureEvent):
    """
    A pathological process, when viewed as an exposure, representing an precondition, leading to or influencing an
    outcome, e.g. autoimmunity leading to disease.
    """

    _category: ClassVar[str] = "PathologicalProcessExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    timepoint: Optional[Union[str, TimeType]] = None


@dataclass(config=PydanticConfig)
class PathologicalAnatomicalStructure(AnatomicalEntity, PathologicalEntityMixin):
    """
    An anatomical structure with the potential of have an abnormal or deleterious effect at the subcellular, cellular,
    multicellular, or organismal level.
    """

    _category: ClassVar[str] = "PathologicalAnatomicalStructure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class PathologicalAnatomicalExposure(PathologicalAnatomicalStructure, ExposureEvent):
    """
    An abnormal anatomical structure, when viewed as an exposure, representing an precondition, leading to or
    influencing an outcome, e.g. thrombosis leading to an ischemic disease outcome.
    """

    _category: ClassVar[str] = "PathologicalAnatomicalExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    timepoint: Optional[Union[str, TimeType]] = None


@dataclass(config=PydanticConfig)
class DiseaseOrPhenotypicFeatureExposure(
    DiseaseOrPhenotypicFeature, ExposureEvent, PathologicalEntityMixin
):
    """
    A disease or phenotypic feature state, when viewed as an exposure, represents an precondition, leading to or
    influencing an outcome, e.g. HIV predisposing an individual to infections; a relative deficiency of skin
    pigmentation predisposing an individual to skin cancer.
    """

    _category: ClassVar[str] = "DiseaseOrPhenotypicFeatureExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    timepoint: Optional[Union[str, TimeType]] = None


@dataclass(config=PydanticConfig)
class ChemicalExposure(ChemicalSubstance, ExposureEvent):
    """
    A chemical exposure is an intake of a particular chemical substance, other than a drug.
    """

    _category: ClassVar[str] = "ChemicalExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    timepoint: Optional[Union[str, TimeType]] = None


@dataclass(config=PydanticConfig)
class ComplexChemicalExposure(ChemicalExposure, Mixture):
    """
    A complex chemical exposure is an intake of a chemical mixture (e.g. gasoline), other than a drug.
    """

    _category: ClassVar[str] = "ComplexChemicalExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    has_constituent: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(
        default_factory=list
    )


@dataclass(config=PydanticConfig)
class DrugExposure(Drug, ExposureEvent):
    """
    A drug exposure is an intake of a particular drug.
    """

    _category: ClassVar[str] = "DrugExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    timepoint: Optional[Union[str, TimeType]] = None


@dataclass(config=PydanticConfig)
class DrugToGeneInteractionExposure(DrugExposure, GeneGroupingMixin):
    """
    drug to gene interaction exposure is a drug exposure is where the interactions of the drug with specific genes are
    known to constitute an 'exposure' to the organism, leading to or influencing an outcome.
    """

    _category: ClassVar[str] = "DrugToGeneInteractionExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    has_gene_or_gene_product: Optional[
        Union[Union[str, Curie, Gene], List[Union[str, Curie, Gene]]]
    ] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class Treatment(NamedThing, ExposureEvent, ChemicalOrDrugOrTreatment):
    """
    A treatment is targeted at a disease or phenotype and may involve multiple drug 'exposures', medical devices
    and/or procedures
    """

    _category: ClassVar[str] = "Treatment"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    has_drug: Optional[Union[Union[str, Curie, Drug], List[Union[str, Curie, Drug]]]] = field(
        default_factory=list
    )
    has_device: Optional[Union[Union[str, Curie, Device], List[Union[str, Curie, Device]]]] = field(
        default_factory=list
    )
    has_procedure: Optional[
        Union[Union[str, Curie, Procedure], List[Union[str, Curie, Procedure]]]
    ] = field(default_factory=list)
    timepoint: Optional[Union[str, TimeType]] = None


@dataclass(config=PydanticConfig)
class BioticExposure(OrganismTaxon, ExposureEvent):
    """
    An external biotic exposure is an intake of (sometimes pathological) biological organisms (including viruses).
    """

    _category: ClassVar[str] = "BioticExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    timepoint: Optional[Union[str, TimeType]] = None


@dataclass(config=PydanticConfig)
class GeographicExposure(GeographicLocation, ExposureEvent):
    """
    A geographic exposure is a factor relating to geographic proximity to some impactful entity.
    """

    _category: ClassVar[str] = "GeographicExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    timepoint: Optional[Union[str, TimeType]] = None


@dataclass(config=PydanticConfig)
class EnvironmentalExposure(EnvironmentalProcess, ExposureEvent):
    """
    A environmental exposure is a factor relating to abiotic processes in the environment including sunlight (UV-B),
    atmospheric (heat, cold, general pollution) and water-born contaminants.
    """

    _category: ClassVar[str] = "EnvironmentalExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    timepoint: Optional[Union[str, TimeType]] = None


@dataclass(config=PydanticConfig)
class BehavioralExposure(Behavior, ExposureEvent):
    """
    A behavioral exposure is a factor relating to behavior impacting an individual.
    """

    _category: ClassVar[str] = "BehavioralExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    timepoint: Optional[Union[str, TimeType]] = None


@dataclass(config=PydanticConfig)
class SocioeconomicExposure(Behavior, ExposureEvent):
    """
    A socioeconomic exposure is a factor relating to social and financial status of an affected individual (e.g.
    poverty).
    """

    _category: ClassVar[str] = "SocioeconomicExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category", "has_attribute"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None
    has_attribute: Union[
        Union[str, SocioeconomicAttribute], List[Union[str, SocioeconomicAttribute]]
    ] = None
    timepoint: Optional[Union[str, TimeType]] = None


class Outcome:
    """
    An entity that has the role of being the consequence of an exposure event. This is an abstract mixin grouping of
    various categories of possible biological or non-biological (e.g. clinical) outcomes.
    """


@dataclass(config=PydanticConfig)
class PathologicalProcessOutcome(PathologicalProcess, Outcome):
    """
    An outcome resulting from an exposure event which is the manifestation of a pathological process.
    """

    _category: ClassVar[str] = "PathologicalProcessOutcome"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class PathologicalAnatomicalOutcome(PathologicalAnatomicalStructure, Outcome):
    """
    An outcome resulting from an exposure event which is the manifestation of an abnormal anatomical structure.
    """

    _category: ClassVar[str] = "PathologicalAnatomicalOutcome"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class DiseaseOrPhenotypicFeatureOutcome(DiseaseOrPhenotypicFeature, Outcome):
    """
    Physiological outcomes resulting from an exposure event which is the manifestation of a disease or other
    characteristic phenotype.
    """

    _category: ClassVar[str] = "DiseaseOrPhenotypicFeatureOutcome"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class BehavioralOutcome(Behavior, Outcome):
    """
    An outcome resulting from an exposure event which is the manifestation of human behavior.
    """

    _category: ClassVar[str] = "BehavioralOutcome"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class HospitalizationOutcome(Hospitalization, Outcome):
    """
    An outcome resulting from an exposure event which is the increased manifestation of acute (e.g. emergency room
    visit) or chronic (inpatient) hospitalization.
    """

    _category: ClassVar[str] = "HospitalizationOutcome"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class MortalityOutcome(Death, Outcome):
    """
    An outcome of death from resulting from an exposure event.
    """

    _category: ClassVar[str] = "MortalityOutcome"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class EpidemiologicalOutcome(BiologicalEntity, Outcome):
    """
    An epidemiological outcome, such as societal disease burden, resulting from an exposure event.
    """

    _category: ClassVar[str] = "EpidemiologicalOutcome"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class SocioeconomicOutcome(Behavior, Outcome):
    """
    An general social or economic outcome, such as healthcare costs, utilization, etc., resulting from an exposure
    event
    """

    _category: ClassVar[str] = "SocioeconomicOutcome"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    id: Union[str, Curie] = None
    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None


@dataclass(config=PydanticConfig)
class Association(Entity):
    """
    A typed association between two entities, supported by evidence
    """

    _category: ClassVar[str] = "Association"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "object", "relation"]

    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    negated: Optional[bool] = None
    qualifiers: Optional[Union[Union[str, OntologyClass], List[Union[str, OntologyClass]]]] = field(
        default_factory=list
    )
    publications: Optional[
        Union[Union[str, Curie, Publication], List[Union[str, Curie, Publication]]]
    ] = field(default_factory=list)
    type: Optional[str] = None
    category: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(
        default_factory=list
    )


@dataclass(config=PydanticConfig)
class ContributorAssociation(Association):
    """
    Any association between an entity (such as a publication) and various agents that contribute to its realisation
    """

    _category: ClassVar[str] = "ContributorAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "predicate", "object"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, InformationContentEntity] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, Agent] = None
    qualifiers: Optional[Union[Union[str, OntologyClass], List[Union[str, OntologyClass]]]] = field(
        default_factory=list
    )


@dataclass(config=PydanticConfig)
class GenotypeToGenotypePartAssociation(Association):
    """
    Any association between one genotype and a genotypic entity that is a sub-component of it
    """

    _category: ClassVar[str] = "GenotypeToGenotypePartAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "predicate", "subject", "object"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    subject: Union[str, Curie, Genotype] = None
    object: Union[str, Curie, Genotype] = None


@dataclass(config=PydanticConfig)
class GenotypeToGeneAssociation(Association):
    """
    Any association between a genotype and a gene. The genotype have have multiple variants in that gene or a single
    one. There is no assumption of cardinality
    """

    _category: ClassVar[str] = "GenotypeToGeneAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "predicate", "subject", "object"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    subject: Union[str, Curie, Genotype] = None
    object: Union[str, Curie, Gene] = None


@dataclass(config=PydanticConfig)
class GenotypeToVariantAssociation(Association):
    """
    Any association between a genotype and a sequence variant.
    """

    _category: ClassVar[str] = "GenotypeToVariantAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "predicate", "subject", "object"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    subject: Union[str, Curie, Genotype] = None
    object: Union[str, Curie, SequenceVariant] = None


@dataclass(config=PydanticConfig)
class GeneToGeneAssociation(Association):
    """
    abstract parent class for different kinds of gene-gene or gene product to gene product relationships. Includes
    homology and interaction.
    """

    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, GeneOrGeneProduct] = None
    object: Union[str, GeneOrGeneProduct] = None


@dataclass(config=PydanticConfig)
class GeneToGeneHomologyAssociation(GeneToGeneAssociation):
    """
    A homology association between two genes. May be orthology (in which case the species of subject and object should
    differ) or paralogy (in which case the species may be the same)
    """

    _category: ClassVar[str] = "GeneToGeneHomologyAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, GeneOrGeneProduct] = None
    object: Union[str, GeneOrGeneProduct] = None
    predicate: Union[str, Curie] = None


@dataclass(config=PydanticConfig)
class GeneExpressionMixin:
    """
    Observed gene expression intensity, context (site, stage) and associated phenotypic status within which the
    expression occurs.
    """

    quantifier_qualifier: Optional[Union[str, OntologyClass]] = None
    expression_site: Optional[Union[str, Curie, AnatomicalEntity]] = None
    stage_qualifier: Optional[Union[str, Curie, LifeStage]] = None
    phenotypic_state: Optional[Union[str, Curie, DiseaseOrPhenotypicFeature]] = None


@dataclass(config=PydanticConfig)
class GeneToGeneCoexpressionAssociation(GeneToGeneAssociation, GeneExpressionMixin):
    """
    Indicates that two genes are co-expressed, generally under the same conditions.
    """

    _category: ClassVar[str] = "GeneToGeneCoexpressionAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, GeneOrGeneProduct] = None
    object: Union[str, GeneOrGeneProduct] = None
    predicate: Union[str, Curie] = None
    quantifier_qualifier: Optional[Union[str, OntologyClass]] = None
    expression_site: Optional[Union[str, Curie, AnatomicalEntity]] = None
    stage_qualifier: Optional[Union[str, Curie, LifeStage]] = None
    phenotypic_state: Optional[Union[str, Curie, DiseaseOrPhenotypicFeature]] = None


@dataclass(config=PydanticConfig)
class PairwiseGeneToGeneInteraction(GeneToGeneAssociation):
    """
    An interaction between two genes or two gene products. May be physical (e.g. protein binding) or genetic (between
    genes). May be symmetric (e.g. protein interaction) or directed (e.g. phosphorylation)
    """

    _category: ClassVar[str] = "PairwiseGeneToGeneInteraction"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "object", "predicate", "relation"]

    id: Union[str, Curie] = None
    subject: Union[str, GeneOrGeneProduct] = None
    object: Union[str, GeneOrGeneProduct] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None


@dataclass(config=PydanticConfig)
class PairwiseMolecularInteraction(PairwiseGeneToGeneInteraction):
    """
    An interaction at the molecular level between two physical entities
    """

    _category: ClassVar[str] = "PairwiseMolecularInteraction"
    _required_attributes: ClassVar[List[str]] = ["subject", "id", "predicate", "relation", "object"]

    id: Union[str, Curie] = None
    subject: Union[str, Curie, MolecularEntity] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    object: Union[str, Curie, MolecularEntity] = None
    interacting_molecules_category: Optional[Union[str, OntologyClass]] = None


@dataclass(config=PydanticConfig)
class CellLineToEntityAssociationMixin:
    """
    An relationship between a cell line and another entity
    """

    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[str, Curie, CellLine] = None


@dataclass(config=PydanticConfig)
class MolecularEntityToEntityAssociationMixin:
    """
    An interaction between a molecular entity and another entity
    """

    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[str, Curie, MolecularEntity] = None


@dataclass(config=PydanticConfig)
class DrugToEntityAssociationMixin(MolecularEntityToEntityAssociationMixin):
    """
    An interaction between a drug and another entity
    """

    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[str, Curie, Drug] = None


@dataclass(config=PydanticConfig)
class ChemicalToEntityAssociationMixin(MolecularEntityToEntityAssociationMixin):
    """
    An interaction between a chemical entity and another entity
    """

    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[str, Curie, ChemicalSubstance] = None


@dataclass(config=PydanticConfig)
class CaseToEntityAssociationMixin:
    """
    An abstract association for use where the case is the subject
    """

    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[str, Curie, Case] = None


@dataclass(config=PydanticConfig)
class ChemicalToChemicalAssociation(Association, ChemicalToEntityAssociationMixin):
    """
    A relationship between two chemical entities. This can encompass actual interactions as well as temporal causal
    edges, e.g. one chemical converted to another.
    """

    _category: ClassVar[str] = "ChemicalToChemicalAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "relation", "object"]

    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    object: Union[str, Curie, ChemicalSubstance] = None


@dataclass(config=PydanticConfig)
class ChemicalToChemicalDerivationAssociation(ChemicalToChemicalAssociation):
    """
    A causal relationship between two chemical entities, where the subject represents the upstream entity and the
    object represents the downstream. For any such association there is an implicit reaction:
    IF
    R has-input C1 AND
    R has-output C2 AND
    R enabled-by P AND
    R type Reaction
    THEN
    C1 derives-into C2 <<catalyst qualifier P>>
    """

    _category: ClassVar[str] = "ChemicalToChemicalDerivationAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, ChemicalSubstance] = None
    object: Union[str, Curie, ChemicalSubstance] = None
    predicate: Union[str, Curie] = None
    catalyst_qualifier: Optional[
        Union[Union[str, MacromolecularMachineMixin], List[Union[str, MacromolecularMachineMixin]]]
    ] = field(default_factory=list)


@dataclass(config=PydanticConfig)
class ChemicalToPathwayAssociation(Association, ChemicalToEntityAssociationMixin):
    """
    An interaction between a chemical entity and a biological process or pathway.
    """

    _category: ClassVar[str] = "ChemicalToPathwayAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "relation", "object"]

    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    object: Union[str, Curie, Pathway] = None


@dataclass(config=PydanticConfig)
class ChemicalToGeneAssociation(Association, ChemicalToEntityAssociationMixin):
    """
    An interaction between a chemical entity and a gene or gene product.
    """

    _category: ClassVar[str] = "ChemicalToGeneAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "relation", "object"]

    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    object: Union[str, GeneOrGeneProduct] = None


@dataclass(config=PydanticConfig)
class DrugToGeneAssociation(Association, DrugToEntityAssociationMixin):
    """
    An interaction between a drug and a gene or gene product.
    """

    _category: ClassVar[str] = "DrugToGeneAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "relation", "object"]

    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    object: Union[str, GeneOrGeneProduct] = None


@dataclass(config=PydanticConfig)
class MaterialSampleToEntityAssociationMixin:
    """
    An association between a material sample and something.
    """

    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[str, Curie, MaterialSample] = None


@dataclass(config=PydanticConfig)
class MaterialSampleDerivationAssociation(Association):
    """
    An association between a material sample and the material entity from which it is derived.
    """

    _category: ClassVar[str] = "MaterialSampleDerivationAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, MaterialSample] = None
    object: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None


@dataclass(config=PydanticConfig)
class DiseaseToEntityAssociationMixin:

    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[str, Curie, Disease] = None


@dataclass(config=PydanticConfig)
class EntityToExposureEventAssociationMixin:
    """
    An association between some entity and an exposure event.
    """

    _required_attributes: ClassVar[List[str]] = ["object"]

    object: Union[str, ExposureEvent] = None


@dataclass(config=PydanticConfig)
class DiseaseToExposureEventAssociation(
    Association, DiseaseToEntityAssociationMixin, EntityToExposureEventAssociationMixin
):
    """
    An association between an exposure event and a disease.
    """

    _category: ClassVar[str] = "DiseaseToExposureEventAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "object", "relation"]

    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None


@dataclass(config=PydanticConfig)
class ExposureEventToEntityAssociationMixin:
    """
    An association between some exposure event and some entity.
    """

    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[str, ExposureEvent] = None


@dataclass(config=PydanticConfig)
class EntityToOutcomeAssociationMixin:
    """
    An association between some entity and an outcome
    """

    _required_attributes: ClassVar[List[str]] = ["object"]

    object: Union[str, Outcome] = None


@dataclass(config=PydanticConfig)
class ExposureEventToOutcomeAssociation(
    Association, ExposureEventToEntityAssociationMixin, EntityToOutcomeAssociationMixin
):
    """
    An association between an exposure event and an outcome.
    """

    _category: ClassVar[str] = "ExposureEventToOutcomeAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "object", "relation"]

    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    has_population_context: Optional[Union[str, Curie, PopulationOfIndividualOrganisms]] = None
    has_temporal_context: Optional[Union[str, TimeType]] = None


@dataclass(config=PydanticConfig)
class FrequencyQualifierMixin:
    """
    Qualifier for frequency type associations
    """

    frequency_qualifier: Optional[Union[str, FrequencyValue]] = None


@dataclass(config=PydanticConfig)
class EntityToFeatureOrDiseaseQualifiersMixin(FrequencyQualifierMixin):
    """
    Qualifiers for entity to disease or phenotype associations.
    """

    severity_qualifier: Optional[Union[str, SeverityValue]] = None
    onset_qualifier: Optional[Union[str, Onset]] = None


@dataclass(config=PydanticConfig)
class EntityToPhenotypicFeatureAssociationMixin(EntityToFeatureOrDiseaseQualifiersMixin):

    _required_attributes: ClassVar[List[str]] = ["object"]

    object: Union[str, Curie, PhenotypicFeature] = None
    sex_qualifier: Optional[Union[str, BiologicalSex]] = None
    description: Optional[Union[str, NarrativeText]] = None


@dataclass(config=PydanticConfig)
class EntityToDiseaseAssociationMixin(EntityToFeatureOrDiseaseQualifiersMixin):
    """
    mixin class for any association whose object (target node) is a disease
    """

    _required_attributes: ClassVar[List[str]] = ["object"]

    object: Union[str, Curie, Disease] = None


@dataclass(config=PydanticConfig)
class DiseaseOrPhenotypicFeatureToEntityAssociationMixin:

    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[str, Curie, DiseaseOrPhenotypicFeature] = None


@dataclass(config=PydanticConfig)
class DiseaseOrPhenotypicFeatureAssociationToLocationAssociation(
    Association, DiseaseOrPhenotypicFeatureToEntityAssociationMixin
):

    _category: ClassVar[str] = "DiseaseOrPhenotypicFeatureAssociationToLocationAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "relation", "object"]

    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    object: Union[str, Curie, AnatomicalEntity] = None


@dataclass(config=PydanticConfig)
class DiseaseOrPhenotypicFeatureToLocationAssociation(
    Association, DiseaseOrPhenotypicFeatureToEntityAssociationMixin
):
    """
    An association between either a disease or a phenotypic feature and an anatomical entity, where the
    disease/feature manifests in that site.
    """

    _category: ClassVar[str] = "DiseaseOrPhenotypicFeatureToLocationAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "relation", "object"]

    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    object: Union[str, Curie, AnatomicalEntity] = None


@dataclass(config=PydanticConfig)
class EntityToDiseaseOrPhenotypicFeatureAssociationMixin:

    _required_attributes: ClassVar[List[str]] = ["object"]

    object: Union[str, Curie, DiseaseOrPhenotypicFeature] = None


@dataclass(config=PydanticConfig)
class CellLineToDiseaseOrPhenotypicFeatureAssociation(
    Association,
    CellLineToEntityAssociationMixin,
    EntityToDiseaseOrPhenotypicFeatureAssociationMixin,
):
    """
    An relationship between a cell line and a disease or a phenotype, where the cell line is derived from an
    individual with that disease or phenotype.
    """

    _category: ClassVar[str] = "CellLineToDiseaseOrPhenotypicFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "object", "relation", "subject"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, DiseaseOrPhenotypicFeature] = None


@dataclass(config=PydanticConfig)
class ChemicalToDiseaseOrPhenotypicFeatureAssociation(
    Association,
    ChemicalToEntityAssociationMixin,
    EntityToDiseaseOrPhenotypicFeatureAssociationMixin,
):
    """
    An interaction between a chemical entity and a phenotype or disease, where the presence of the chemical gives rise
    to or exacerbates the phenotype.
    """

    _category: ClassVar[str] = "ChemicalToDiseaseOrPhenotypicFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "relation", "object"]

    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    object: Union[str, Curie, DiseaseOrPhenotypicFeature] = None


@dataclass(config=PydanticConfig)
class MaterialSampleToDiseaseOrPhenotypicFeatureAssociation(
    Association,
    MaterialSampleToEntityAssociationMixin,
    EntityToDiseaseOrPhenotypicFeatureAssociationMixin,
):
    """
    An association between a material sample and a disease or phenotype.
    """

    _category: ClassVar[str] = "MaterialSampleToDiseaseOrPhenotypicFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "object", "relation"]

    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None


@dataclass(config=PydanticConfig)
class GenotypeToEntityAssociationMixin:

    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[str, Curie, Genotype] = None


@dataclass(config=PydanticConfig)
class GenotypeToPhenotypicFeatureAssociation(
    Association, EntityToPhenotypicFeatureAssociationMixin, GenotypeToEntityAssociationMixin
):
    """
    Any association between one genotype and a phenotypic feature, where having the genotype confers the phenotype,
    either in isolation or through environment
    """

    _category: ClassVar[str] = "GenotypeToPhenotypicFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "object", "relation", "predicate", "subject"]

    id: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    subject: Union[str, Curie, Genotype] = None
    sex_qualifier: Optional[Union[str, BiologicalSex]] = None


@dataclass(config=PydanticConfig)
class ExposureEventToPhenotypicFeatureAssociation(
    Association, EntityToPhenotypicFeatureAssociationMixin
):
    """
    Any association between an environment and a phenotypic feature, where being in the environment influences the
    phenotype.
    """

    _category: ClassVar[str] = "ExposureEventToPhenotypicFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "object", "relation", "subject"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    subject: Union[str, ExposureEvent] = None
    sex_qualifier: Optional[Union[str, BiologicalSex]] = None


@dataclass(config=PydanticConfig)
class DiseaseToPhenotypicFeatureAssociation(
    Association, EntityToPhenotypicFeatureAssociationMixin, DiseaseToEntityAssociationMixin
):
    """
    An association between a disease and a phenotypic feature in which the phenotypic feature is associated with the
    disease in some way.
    """

    _category: ClassVar[str] = "DiseaseToPhenotypicFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "object", "relation"]

    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    sex_qualifier: Optional[Union[str, BiologicalSex]] = None


@dataclass(config=PydanticConfig)
class CaseToPhenotypicFeatureAssociation(
    Association, EntityToPhenotypicFeatureAssociationMixin, CaseToEntityAssociationMixin
):
    """
    An association between a case (e.g. individual patient) and a phenotypic feature in which the individual has or
    has had the phenotype.
    """

    _category: ClassVar[str] = "CaseToPhenotypicFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "object", "relation"]

    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    sex_qualifier: Optional[Union[str, BiologicalSex]] = None


@dataclass(config=PydanticConfig)
class BehaviorToBehavioralFeatureAssociation(
    Association, EntityToPhenotypicFeatureAssociationMixin
):
    """
    An association between an aggregate behavior and a behavioral feature manifested by the individual exhibited or
    has exhibited the behavior.
    """

    _category: ClassVar[str] = "BehaviorToBehavioralFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, Behavior] = None
    object: Union[str, Curie, BehavioralFeature] = None
    sex_qualifier: Optional[Union[str, BiologicalSex]] = None


@dataclass(config=PydanticConfig)
class GeneToEntityAssociationMixin:

    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[str, GeneOrGeneProduct] = None


@dataclass(config=PydanticConfig)
class VariantToEntityAssociationMixin:

    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[str, Curie, SequenceVariant] = None


@dataclass(config=PydanticConfig)
class GeneToPhenotypicFeatureAssociation(
    Association, EntityToPhenotypicFeatureAssociationMixin, GeneToEntityAssociationMixin
):

    _category: ClassVar[str] = "GeneToPhenotypicFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "object", "relation", "subject"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    subject: Union[str, GeneOrGeneProduct] = None
    sex_qualifier: Optional[Union[str, BiologicalSex]] = None


@dataclass(config=PydanticConfig)
class GeneToDiseaseAssociation(
    Association, EntityToDiseaseAssociationMixin, GeneToEntityAssociationMixin
):

    _category: ClassVar[str] = "GeneToDiseaseAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "object", "relation", "subject"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    subject: Union[str, GeneOrGeneProduct] = None


@dataclass(config=PydanticConfig)
class VariantToGeneAssociation(Association, VariantToEntityAssociationMixin):
    """
    An association between a variant and a gene, where the variant has a genetic association with the gene (i.e. is in
    linkage disequilibrium)
    """

    _category: ClassVar[str] = "VariantToGeneAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "relation", "object", "predicate"]

    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    object: Union[str, Curie, Gene] = None
    predicate: Union[str, Curie] = None


@dataclass(config=PydanticConfig)
class VariantToGeneExpressionAssociation(VariantToGeneAssociation, GeneExpressionMixin):
    """
    An association between a variant and expression of a gene (i.e. e-QTL)
    """

    _category: ClassVar[str] = "VariantToGeneExpressionAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "relation", "object", "predicate"]

    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    object: Union[str, Curie, Gene] = None
    predicate: Union[str, Curie] = None
    quantifier_qualifier: Optional[Union[str, OntologyClass]] = None
    expression_site: Optional[Union[str, Curie, AnatomicalEntity]] = None
    stage_qualifier: Optional[Union[str, Curie, LifeStage]] = None
    phenotypic_state: Optional[Union[str, Curie, DiseaseOrPhenotypicFeature]] = None


@dataclass(config=PydanticConfig)
class VariantToPopulationAssociation(
    Association, VariantToEntityAssociationMixin, FrequencyQuantifier, FrequencyQualifierMixin
):
    """
    An association between a variant and a population, where the variant has particular frequency in the population
    """

    _category: ClassVar[str] = "VariantToPopulationAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, SequenceVariant] = None
    object: Union[str, Curie, PopulationOfIndividualOrganisms] = None
    has_quotient: Optional[float] = None
    has_count: Optional[int] = None
    has_total: Optional[int] = None
    has_percentage: Optional[float] = None
    frequency_qualifier: Optional[Union[str, FrequencyValue]] = None


@dataclass(config=PydanticConfig)
class PopulationToPopulationAssociation(Association):
    """
    An association between a two populations
    """

    _category: ClassVar[str] = "PopulationToPopulationAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, PopulationOfIndividualOrganisms] = None
    object: Union[str, Curie, PopulationOfIndividualOrganisms] = None
    predicate: Union[str, Curie] = None


@dataclass(config=PydanticConfig)
class VariantToPhenotypicFeatureAssociation(
    Association, VariantToEntityAssociationMixin, EntityToPhenotypicFeatureAssociationMixin
):

    _category: ClassVar[str] = "VariantToPhenotypicFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "object", "relation", "subject"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, SequenceVariant] = None
    sex_qualifier: Optional[Union[str, BiologicalSex]] = None


@dataclass(config=PydanticConfig)
class VariantToDiseaseAssociation(
    Association, VariantToEntityAssociationMixin, EntityToDiseaseAssociationMixin
):

    _category: ClassVar[str] = "VariantToDiseaseAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "predicate", "object"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None


@dataclass(config=PydanticConfig)
class GenotypeToDiseaseAssociation(
    Association, GenotypeToEntityAssociationMixin, EntityToDiseaseAssociationMixin
):

    _category: ClassVar[str] = "GenotypeToDiseaseAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "predicate", "object"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None


@dataclass(config=PydanticConfig)
class ModelToDiseaseAssociationMixin:
    """
    This mixin is used for any association class for which the subject (source node) plays the role of a 'model', in
    that it recapitulates some features of the disease in a way that is useful for studying the disease outside a
    patient carrying the disease
    """

    _required_attributes: ClassVar[List[str]] = ["subject", "predicate"]

    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None


@dataclass(config=PydanticConfig)
class GeneAsAModelOfDiseaseAssociation(
    GeneToDiseaseAssociation, ModelToDiseaseAssociationMixin, EntityToDiseaseAssociationMixin
):

    _category: ClassVar[str] = "GeneAsAModelOfDiseaseAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "object", "relation", "subject"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    subject: Union[str, GeneOrGeneProduct] = None


@dataclass(config=PydanticConfig)
class VariantAsAModelOfDiseaseAssociation(
    VariantToDiseaseAssociation, ModelToDiseaseAssociationMixin, EntityToDiseaseAssociationMixin
):

    _category: ClassVar[str] = "VariantAsAModelOfDiseaseAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "predicate", "object", "subject"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    subject: Union[str, Curie, SequenceVariant] = None


@dataclass(config=PydanticConfig)
class GenotypeAsAModelOfDiseaseAssociation(
    GenotypeToDiseaseAssociation, ModelToDiseaseAssociationMixin, EntityToDiseaseAssociationMixin
):

    _category: ClassVar[str] = "GenotypeAsAModelOfDiseaseAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "predicate", "object", "subject"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    subject: Union[str, Curie, Genotype] = None


@dataclass(config=PydanticConfig)
class CellLineAsAModelOfDiseaseAssociation(
    CellLineToDiseaseOrPhenotypicFeatureAssociation,
    ModelToDiseaseAssociationMixin,
    EntityToDiseaseAssociationMixin,
):

    _category: ClassVar[str] = "CellLineAsAModelOfDiseaseAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "object", "relation", "subject"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, CellLine] = None


@dataclass(config=PydanticConfig)
class OrganismalEntityAsAModelOfDiseaseAssociation(
    Association, ModelToDiseaseAssociationMixin, EntityToDiseaseAssociationMixin
):

    _category: ClassVar[str] = "OrganismalEntityAsAModelOfDiseaseAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "object", "relation", "subject"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, OrganismalEntity] = None


@dataclass(config=PydanticConfig)
class GeneHasVariantThatContributesToDiseaseAssociation(GeneToDiseaseAssociation):

    _category: ClassVar[str] = "GeneHasVariantThatContributesToDiseaseAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "object", "relation", "subject"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    subject: Union[str, GeneOrGeneProduct] = None
    sequence_variant_qualifier: Optional[Union[str, Curie, SequenceVariant]] = None


@dataclass(config=PydanticConfig)
class GeneToExpressionSiteAssociation(Association):
    """
    An association between a gene and an expression site, possibly qualified by stage/timing info.
    """

    _category: ClassVar[str] = "GeneToExpressionSiteAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, GeneOrGeneProduct] = None
    object: Union[str, Curie, AnatomicalEntity] = None
    predicate: Union[str, Curie] = None
    stage_qualifier: Optional[Union[str, Curie, LifeStage]] = None
    quantifier_qualifier: Optional[Union[str, OntologyClass]] = None


@dataclass(config=PydanticConfig)
class SequenceVariantModulatesTreatmentAssociation(Association):
    """
    An association between a sequence variant and a treatment or health intervention. The treatment object itself
    encompasses both the disease and the drug used.
    """

    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, SequenceVariant] = None
    object: Union[str, Curie, Treatment] = None


@dataclass(config=PydanticConfig)
class FunctionalAssociation(Association):
    """
    An association between a macromolecular machine mixin (gene, gene product or complex of gene products) and either
    a molecular activity, a biological process or a cellular location in which a function is executed.
    """

    _category: ClassVar[str] = "FunctionalAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, MacromolecularMachineMixin] = None
    object: Union[str, GeneOntologyClass] = None


@dataclass(config=PydanticConfig)
class MacromolecularMachineToEntityAssociationMixin:
    """
    an association which has a macromolecular machine mixin as a subject
    """

    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[str, Curie, NamedThing] = None


@dataclass(config=PydanticConfig)
class MacromolecularMachineToMolecularActivityAssociation(
    FunctionalAssociation, MacromolecularMachineToEntityAssociationMixin
):
    """
    A functional association between a macromolecular machine (gene, gene product or complex) and a molecular activity
    (as represented in the GO molecular function branch), where the entity carries out the activity, or contributes to
    its execution.
    """

    _category: ClassVar[str] = "MacromolecularMachineToMolecularActivityAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, MacromolecularMachineMixin] = None
    object: Union[str, Curie, MolecularActivity] = None


@dataclass(config=PydanticConfig)
class MacromolecularMachineToBiologicalProcessAssociation(
    FunctionalAssociation, MacromolecularMachineToEntityAssociationMixin
):
    """
    A functional association between a macromolecular machine (gene, gene product or complex) and a biological process
    or pathway (as represented in the GO biological process branch), where the entity carries out some part of the
    process, regulates it, or acts upstream of it.
    """

    _category: ClassVar[str] = "MacromolecularMachineToBiologicalProcessAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, MacromolecularMachineMixin] = None
    object: Union[str, Curie, BiologicalProcess] = None


@dataclass(config=PydanticConfig)
class MacromolecularMachineToCellularComponentAssociation(
    FunctionalAssociation, MacromolecularMachineToEntityAssociationMixin
):
    """
    A functional association between a macromolecular machine (gene, gene product or complex) and a cellular component
    (as represented in the GO cellular component branch), where the entity carries out its function in the cellular
    component.
    """

    _category: ClassVar[str] = "MacromolecularMachineToCellularComponentAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, MacromolecularMachineMixin] = None
    object: Union[str, Curie, CellularComponent] = None


@dataclass(config=PydanticConfig)
class GeneToGoTermAssociation(FunctionalAssociation):

    _category: ClassVar[str] = "GeneToGoTermAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, MolecularEntity] = None
    object: Union[str, GeneOntologyClass] = None


@dataclass(config=PydanticConfig)
class SequenceAssociation(Association):
    """
    An association between a sequence feature and a genomic entity it is localized to.
    """

    _category: ClassVar[str] = "SequenceAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "object", "relation"]

    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None


@dataclass(config=PydanticConfig)
class GenomicSequenceLocalization(SequenceAssociation):
    """
    A relationship between a sequence feature and a genomic entity it is localized to. The reference entity may be a
    chromosome, chromosome region or information entity such as a contig.
    """

    _category: ClassVar[str] = "GenomicSequenceLocalization"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, GenomicEntity] = None
    object: Union[str, Curie, GenomicEntity] = None
    predicate: Union[str, Curie] = None
    start_interbase_coordinate: Optional[int] = None
    end_interbase_coordinate: Optional[int] = None
    genome_build: Optional[str] = None
    strand: Optional[str] = None
    phase: Optional[str] = None


@dataclass(config=PydanticConfig)
class SequenceFeatureRelationship(Association):
    """
    For example, a particular exon is part of a particular transcript or gene
    """

    _category: ClassVar[str] = "SequenceFeatureRelationship"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, GenomicEntity] = None
    object: Union[str, Curie, GenomicEntity] = None


@dataclass(config=PydanticConfig)
class TranscriptToGeneRelationship(SequenceFeatureRelationship):
    """
    A gene is a collection of transcripts
    """

    _category: ClassVar[str] = "TranscriptToGeneRelationship"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, Transcript] = None
    object: Union[str, Curie, Gene] = None


@dataclass(config=PydanticConfig)
class GeneToGeneProductRelationship(SequenceFeatureRelationship):
    """
    A gene is transcribed and potentially translated to a gene product
    """

    _category: ClassVar[str] = "GeneToGeneProductRelationship"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, Gene] = None
    object: Union[str, GeneProductMixin] = None
    predicate: Union[str, Curie] = None


@dataclass(config=PydanticConfig)
class ExonToTranscriptRelationship(SequenceFeatureRelationship):
    """
    A transcript is formed from multiple exons
    """

    _category: ClassVar[str] = "ExonToTranscriptRelationship"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, Exon] = None
    object: Union[str, Curie, Transcript] = None


@dataclass(config=PydanticConfig)
class GeneRegulatoryRelationship(Association):
    """
    A regulatory relationship between two genes
    """

    _category: ClassVar[str] = "GeneRegulatoryRelationship"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "predicate", "subject", "object"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    subject: Union[str, GeneOrGeneProduct] = None
    object: Union[str, GeneOrGeneProduct] = None


@dataclass(config=PydanticConfig)
class AnatomicalEntityToAnatomicalEntityAssociation(Association):

    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, AnatomicalEntity] = None
    object: Union[str, Curie, AnatomicalEntity] = None


@dataclass(config=PydanticConfig)
class AnatomicalEntityToAnatomicalEntityPartOfAssociation(
    AnatomicalEntityToAnatomicalEntityAssociation
):
    """
    A relationship between two anatomical entities where the relationship is mereological, i.e the two entities are
    related by parthood. This includes relationships between cellular components and cells, between cells and tissues,
    tissues and whole organisms
    """

    _category: ClassVar[str] = "AnatomicalEntityToAnatomicalEntityPartOfAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, AnatomicalEntity] = None
    object: Union[str, Curie, AnatomicalEntity] = None
    predicate: Union[str, Curie] = None


@dataclass(config=PydanticConfig)
class AnatomicalEntityToAnatomicalEntityOntogenicAssociation(
    AnatomicalEntityToAnatomicalEntityAssociation
):
    """
    A relationship between two anatomical entities where the relationship is ontogenic, i.e. the two entities are
    related by development. A number of different relationship types can be used to specify the precise nature of the
    relationship.
    """

    _category: ClassVar[str] = "AnatomicalEntityToAnatomicalEntityOntogenicAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, AnatomicalEntity] = None
    object: Union[str, Curie, AnatomicalEntity] = None
    predicate: Union[str, Curie] = None


@dataclass(config=PydanticConfig)
class OrganismTaxonToEntityAssociation:
    """
    An association between an organism taxon and another entity
    """

    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[str, Curie, OrganismTaxon] = None


@dataclass(config=PydanticConfig)
class OrganismTaxonToOrganismTaxonAssociation(Association, OrganismTaxonToEntityAssociation):
    """
    A relationship between two organism taxon nodes
    """

    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, OrganismTaxon] = None
    object: Union[str, Curie, OrganismTaxon] = None


@dataclass(config=PydanticConfig)
class OrganismTaxonToOrganismTaxonSpecialization(OrganismTaxonToOrganismTaxonAssociation):
    """
    A child-parent relationship between two taxa. For example: Homo sapiens subclass_of Homo
    """

    _category: ClassVar[str] = "OrganismTaxonToOrganismTaxonSpecialization"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, OrganismTaxon] = None
    object: Union[str, Curie, OrganismTaxon] = None
    predicate: Union[str, Curie] = None


@dataclass(config=PydanticConfig)
class OrganismTaxonToOrganismTaxonInteraction(OrganismTaxonToOrganismTaxonAssociation):
    """
    An interaction relationship between two taxa. This may be a symbiotic relationship (encompassing mutualism and
    parasitism), or it may be non-symbiotic. Example: plague transmitted_by flea; cattle domesticated_by Homo sapiens;
    plague infects Homo sapiens
    """

    _category: ClassVar[str] = "OrganismTaxonToOrganismTaxonInteraction"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, OrganismTaxon] = None
    object: Union[str, Curie, OrganismTaxon] = None
    predicate: Union[str, Curie] = None
    associated_environmental_context: Optional[str] = None


@dataclass(config=PydanticConfig)
class OrganismTaxonToEnvironmentAssociation(Association, OrganismTaxonToEntityAssociation):

    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, OrganismTaxon] = None
    object: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None


predicates = [
    'actively_involved_in',
    'affected_by',
    'affects',
    'affects_abundance_of',
    'affects_activity_of',
    'affects_degradation_of',
    'affects_expression_in',
    'affects_expression_of',
    'affects_folding_of',
    'affects_localization_of',
    'affects_metabolic_processing_of',
    'affects_molecular_modification_of',
    'affects_mutation_rate_of',
    'affects_response_to',
    'affects_risk_for',
    'affects_secretion_of',
    'affects_splicing_of',
    'affects_stability_of',
    'affects_synthesis_of',
    'affects_transport_of',
    'affects_uptake_of',
    'ameliorates',
    'approved_for_treatment_by',
    'approved_to_treat',
    'author',
    'biomarker_for',
    'broad_match',
    'capable_of',
    'caused_by',
    'causes',
    'causes_adverse_event',
    'chemically_similar_to',
    'close_match',
    'coexists_with',
    'coexpressed_with',
    'colocalizes_with',
    'condition_associated_with_gene',
    'contraindicated_for',
    'contributes_to',
    'contributor',
    'correlated_with',
    'decreases_abundance_of',
    'decreases_activity_of',
    'decreases_degradation_of',
    'decreases_expression_of',
    'decreases_folding_of',
    'decreases_localization_of',
    'decreases_metabolic_processing_of',
    'decreases_molecular_interaction',
    'decreases_molecular_modification_of',
    'decreases_mutation_rate_of',
    'decreases_response_to',
    'decreases_secretion_of',
    'decreases_splicing_of',
    'decreases_stability_of',
    'decreases_synthesis_of',
    'decreases_transport_of',
    'decreases_uptake_of',
    'derives_from',
    'derives_into',
    'develops_from',
    'directly_interacts_with',
    'disease_has_basis_in',
    'disrupted_by',
    'disrupts',
    'editor',
    'enabled_by',
    'enables',
    'entity_negatively_regulated_by_entity',
    'entity_negatively_regulates_entity',
    'entity_positively_regulated_by_entity',
    'entity_positively_regulates_entity',
    'entity_regulated_by_entity',
    'entity_regulates_entity',
    'exacerbates',
    'exact_match',
    'expressed_in',
    'expresses',
    'food_component_of',
    'gene_associated_with_condition',
    'gene_product_of',
    'genetic_association',
    'genetically_interacts_with',
    'has_active_ingredient',
    'has_biomarker',
    'has_completed',
    'has_decreased_amount',
    'has_excipient',
    'has_food_component',
    'has_gene_product',
    'has_increased_amount',
    'has_input',
    'has_metabolite',
    'has_molecular_consequence',
    'has_not_completed',
    'has_nutrient',
    'has_output',
    'has_part',
    'has_participant',
    'has_phenotype',
    'has_sequence_location',
    'has_variant_part',
    'homologous_to',
    'in_cell_population_with',
    'in_complex_with',
    'in_linkage_disequilibrium_with',
    'in_pathway_with',
    'in_taxon',
    'increases_abundance_of',
    'increases_activity_of',
    'increases_degradation_of',
    'increases_expression_of',
    'increases_folding_of',
    'increases_localization_of',
    'increases_metabolic_processing_of',
    'increases_molecular_interaction',
    'increases_molecular_modification_of',
    'increases_mutation_rate_of',
    'increases_response_to',
    'increases_secretion_of',
    'increases_splicing_of',
    'increases_stability_of',
    'increases_synthesis_of',
    'increases_transport_of',
    'increases_uptake_of',
    'interacts_with',
    'is_active_ingredient_of',
    'is_excipient_of',
    'is_frameshift_variant_of',
    'is_metabolite_of',
    'is_missense_variant_of',
    'is_nearby_variant_of',
    'is_non_coding_variant_of',
    'is_nonsense_variant_of',
    'is_sequence_variant_of',
    'is_splice_site_variant_of',
    'is_synonymous_variant_of',
    'lacks_part',
    'located_in',
    'location_of',
    'manifestation_of',
    'model_of',
    'molecular_activity_enabled_by',
    'molecular_activity_has_input',
    'molecular_activity_has_output',
    'molecularly_interacts_with',
    'narrow_match',
    'negatively_correlated_with',
    'nutrient_of',
    'occurs_in',
    'opposite_of',
    'organism_taxon_subclass_of',
    'orthologous_to',
    'overlaps',
    'paralogous_to',
    'part_of',
    'participates_in',
    'phenotype_of',
    'physically_interacts_with',
    'positively_correlated_with',
    'preceded_by',
    'precedes',
    'predisposes',
    'prevented_by',
    'prevents',
    'process_negatively_regulated_by_process',
    'process_negatively_regulates_process',
    'process_positively_regulated_by_process',
    'process_positively_regulates_process',
    'process_regulated_by_process',
    'process_regulates_process',
    'produced_by',
    'produces',
    'provider',
    'publisher',
    'related_condition',
    'related_to',
    'same_as',
    'similar_to',
    'subclass_of',
    'superclass_of',
    'temporally_related_to',
    'transcribed_from',
    'transcribed_to',
    'translates_to',
    'translation_of',
    'treated_by',
    'treats',
    'xenologous_to',
]

predicate = namedtuple('biolink_predicate', predicates)(
    *['biolink:' + predicate for predicate in predicates]
)
