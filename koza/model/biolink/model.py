# Auto generated from biolink-model.yaml by pydanticgen.py version: 0.9.0
# Generation date: 2021-05-18 17:18
# Schema: Biolink-Model
#
# id: https://w3id.org/biolink/biolink-model
# description: Entity and association taxonomy and datamodel for life-sciences data
# license: https://creativecommons.org/publicdomain/zero/1.0/

from dataclasses import field
from typing import Optional, List, Union, Dict, ClassVar, Any

from pydantic.dataclasses import dataclass

from koza.validator.model_validator import convert_object_to_scalar, convert_objects_to_scalars

from koza.model.config.pydantic_config import PydanticConfig
from koza.model.curie import Curie
from koza.model.biolink.named_thing import Entity, Publication

metamodel_version = "1.7.0"

# Classes

class OntologyClass():
    """
    a concept or class in an ontology, vocabulary or thesaurus. Note that nodes in a biolink compatible KG can be
    considered both instances of biolink classes, and OWL classes in their own right. In general you should not need
    to use this class directly. Instead, use the appropriate biolink class. For example, for the GO concept of
    endocytosis (GO:0006897), use bl:BiologicalProcess as the type.
    """

class Annotation():
    """
    Biolink Model root class for entity annotations.
    """

@dataclass(config=PydanticConfig)
class QuantityValue(Annotation):
    """
    A value of an attribute that is quantitative and measurable, expressed as a combination of a unit and a numeric
    value
    """
    has_unit: Optional[Union[str, Unit]] = None
    has_numeric_value: Optional[float] = None

@dataclass(config=PydanticConfig)
class Attribute(Annotation):
    """
    A property or characteristic of an entity. For example, an apple may have properties such as color, shape, age,
    crispiness. An environmental sample may have attributes such as depth, lat, long, material.
    """
    has_attribute_type: Union[str, OntologyClass] = None
    name: Optional[Union[str, LabelType]] = None
    has_quantitative_value: Optional[Union[Union[str, QuantityValue], List[Union[str, QuantityValue]]]] = field(default_factory=list)
    has_qualitative_value: Optional[Union[str, Curie, NamedThing]] = None
    iri: Optional[Union[str, Curie]] = None
    source: Optional[Union[str, LabelType]] = None

@dataclass(config=PydanticConfig)
class BiologicalSex(Attribute):
    has_attribute_type: Union[str, OntologyClass] = None

@dataclass(config=PydanticConfig)
class PhenotypicSex(BiologicalSex):
    """
    An attribute corresponding to the phenotypic sex of the individual, based upon the reproductive organs present.
    """
    has_attribute_type: Union[str, OntologyClass] = None

@dataclass(config=PydanticConfig)
class GenotypicSex(BiologicalSex):
    """
    An attribute corresponding to the genotypic sex of the individual, based upon genotypic composition of sex
    chromosomes.
    """
    has_attribute_type: Union[str, OntologyClass] = None

@dataclass(config=PydanticConfig)
class SeverityValue(Attribute):
    """
    describes the severity of a phenotypic feature or disease
    """
    has_attribute_type: Union[str, OntologyClass] = None

class RelationshipQuantifier():

class SensitivityQuantifier(RelationshipQuantifier):

class SpecificityQuantifier(RelationshipQuantifier):

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

class ChemicalOrDrugOrTreatment():

@dataclass(config=PydanticConfig)
class Entity():
    """
    Root Biolink Model class for all things and informational relationships, real or imagined.
    """
    id: Union[str, Curie] = None
    iri: Optional[Union[str, Curie]] = None
    category: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(default_factory=list)
    type: Optional[str] = None
    name: Optional[Union[str, LabelType]] = None
    description: Optional[Union[str, NarrativeText]] = None
    source: Optional[Union[str, LabelType]] = None
    provided_by: Optional[Union[Union[str, Curie, Agent], List[Union[str, Curie, Agent]]]] = field(default_factory=list)
    has_attribute: Optional[Union[Union[str, Attribute], List[Union[str, Attribute]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class NamedThing(Entity):
    """
    a databased entity or concept/class
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

class RelationshipType(OntologyClass):
    """
    An OWL property used as an edge label
    """

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

@dataclass(config=PydanticConfig)
class OrganismTaxon(NamedThing):
    """
    A classification of a set of organisms. Example instances: NCBITaxon:9606 (Homo sapiens), NCBITaxon:2 (Bacteria).
    Can also be used to represent strains or subspecies.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    has_taxonomic_rank: Optional[Union[str, TaxonomicRank]] = None
    subclass_of: Optional[Union[Union[str, Curie, OrganismTaxon], List[Union[str, Curie, OrganismTaxon]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class AdministrativeEntity(NamedThing):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Agent(AdministrativeEntity):
    """
    person, group, organization or project that provides a piece of information (i.e. a knowledge association)
    """
    id: Union[str, Curie, Agent] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    affiliation: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(default_factory=list)
    address: Optional[str] = None
    name: Optional[Union[str, LabelType]] = None

@dataclass(config=PydanticConfig)
class InformationContentEntity(NamedThing):
    """
    a piece of information that typically describes some topic of discourse or is used as support.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    license: Optional[str] = None
    rights: Optional[str] = None
    format: Optional[str] = None
    creation_date: Optional[Union[str, XSDDate]] = None

@dataclass(config=PydanticConfig)
class Dataset(InformationContentEntity):
    """
    an item that refers to a collection of data from a data source.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class DatasetDistribution(InformationContentEntity):
    """
    an item that holds distribution level information about a dataset.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    distribution_download_url: Optional[str] = None

@dataclass(config=PydanticConfig)
class DatasetVersion(InformationContentEntity):
    """
    an item that holds version level information about a dataset.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    has_dataset: Optional[Union[str, Curie, Dataset]] = None
    ingest_date: Optional[str] = None
    has_distribution: Optional[Union[str, Curie, DatasetDistribution]] = None

@dataclass(config=PydanticConfig)
class DatasetSummary(InformationContentEntity):
    """
    an item that holds summary level information about a dataset.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    source_web_page: Optional[str] = None
    source_logo: Optional[str] = None

@dataclass(config=PydanticConfig)
class ConfidenceLevel(InformationContentEntity):
    """
    Level of confidence in a statement
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class EvidenceType(InformationContentEntity):
    """
    Class of evidence that supports an association
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Publication(InformationContentEntity):
    """
    Any published piece of information. Can refer to a whole publication, its encompassing publication (i.e. journal
    or book) or to a part of a publication, if of significant knowledge scope (e.g. a figure, figure legend, or
    section highlighted by NLP). The scope is intended to be general and include information published on the web, as
    well as printed materials, either directly or in one of the Publication Biolink category subclasses.
    """
    id: Union[str, Curie, Publication] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    type: str = None
    authors: Optional[Union[str, List[str]]] = field(default_factory=list)
    pages: Optional[Union[str, List[str]]] = field(default_factory=list)
    summary: Optional[str] = None
    keywords: Optional[Union[str, List[str]]] = field(default_factory=list)
    mesh_terms: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(default_factory=list)
    xref: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(default_factory=list)
    name: Optional[Union[str, LabelType]] = None

@dataclass(config=PydanticConfig)
class Book(Publication):
    """
    This class may rarely be instantiated except if use cases of a given knowledge graph support its utility.
    """
    id: Union[str, Curie, Book] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    type: str = None

@dataclass(config=PydanticConfig)
class BookChapter(Publication):
    id: Union[str, Curie, BookChapter] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    type: str = None
    published_in: Union[str, Curie] = None
    volume: Optional[str] = None
    chapter: Optional[str] = None

@dataclass(config=PydanticConfig)
class Serial(Publication):
    """
    This class may rarely be instantiated except if use cases of a given knowledge graph support its utility.
    """
    id: Union[str, Curie, Serial] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    type: str = None
    iso_abbreviation: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None

@dataclass(config=PydanticConfig)
class Article(Publication):
    id: Union[str, Curie, Article] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    type: str = None
    published_in: Union[str, Curie] = None
    iso_abbreviation: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None

class PhysicalEssenceOrOccurrent():
    """
    Either a physical or processual entity.
    """

class PhysicalEssence(PhysicalEssenceOrOccurrent):
    """
    Semantic mixin concept.  Pertains to entities that have physical properties such as mass, volume, or charge.
    """

@dataclass(config=PydanticConfig)
class PhysicalEntity(NamedThing):
    """
    An entity that has material reality (a.k.a. physical essence).
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

class Occurrent(PhysicalEssenceOrOccurrent):
    """
    A processual entity.
    """

class ActivityAndBehavior(Occurrent):
    """
    Activity or behavior of any independent integral living, organization or mechanical actor in the world
    """

@dataclass(config=PydanticConfig)
class Activity(NamedThing):
    """
    An activity is something that occurs over a period of time and acts upon or with entities; it may include
    consuming, processing, transforming, modifying, relocating, using, or generating entities.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Procedure(NamedThing):
    """
    A series of actions conducted in a certain order or manner
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Phenomenon(NamedThing):
    """
    a fact or situation that is observed to exist or happen, especially one whose cause or explanation is in question
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Device(NamedThing):
    """
    A thing made or adapted for a particular purpose, especially a piece of mechanical or electronic equipment
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

class SubjectOfInvestigation():
    """
    An entity that has the role of being studied in an investigation, study, or experiment
    """

@dataclass(config=PydanticConfig)
class MaterialSample(PhysicalEntity):
    """
    A sample is a limited quantity of something (e.g. an individual or set of individuals from a population, or a
    portion of a substance) to be used for testing, analysis, inspection, investigation, demonstration, or trial use.
    [SIO]
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class PlanetaryEntity(NamedThing):
    """
    Any entity or process that exists at the level of the whole planet
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class EnvironmentalProcess(PlanetaryEntity):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class EnvironmentalFeature(PlanetaryEntity):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class GeographicLocation(PlanetaryEntity):
    """
    a location that can be described in lat/long coordinates
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

@dataclass(config=PydanticConfig)
class GeographicLocationAtTime(GeographicLocation):
    """
    a location that can be described in lat/long coordinates, for a particular time
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    timepoint: Optional[Union[str, TimeType]] = None

@dataclass(config=PydanticConfig)
class BiologicalEntity(NamedThing):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class ThingWithTaxon():
    """
    A mixin that can be used on any entity that can be taxonomically classified. This includes individual organisms;
    genes, their products and other molecular entities; body parts; biological processes
    """
    in_taxon: Optional[Union[Union[str, Curie, OrganismTaxon], List[Union[str, Curie, OrganismTaxon]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class MolecularEntity(BiologicalEntity):
    """
    A gene, gene product, small molecule or macromolecule (including protein complex)"
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    in_taxon: Optional[Union[Union[str, Curie, OrganismTaxon], List[Union[str, Curie, OrganismTaxon]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class BiologicalProcessOrActivity(BiologicalEntity):
    """
    Either an individual molecular activity, or a collection of causally connected molecular activities in a
    biological system.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    has_input: Optional[Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]]] = field(default_factory=list)
    has_output: Optional[Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]]] = field(default_factory=list)
    enabled_by: Optional[Union[Union[str, Curie, PhysicalEntity], List[Union[str, Curie, PhysicalEntity]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class MolecularActivity(BiologicalProcessOrActivity):
    """
    An execution of a molecular function carried out by a gene product or macromolecular complex.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    has_input: Optional[Union[Union[str, Curie, ChemicalSubstance], List[Union[str, Curie, ChemicalSubstance]]]] = field(default_factory=list)
    has_output: Optional[Union[Union[str, Curie, ChemicalSubstance], List[Union[str, Curie, ChemicalSubstance]]]] = field(default_factory=list)
    enabled_by: Optional[Union[Union[str, "MacromolecularMachineMixin"], List[Union[str, "MacromolecularMachineMixin"]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class BiologicalProcess(BiologicalProcessOrActivity):
    """
    One or more causally connected executions of molecular functions
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Pathway(BiologicalProcess):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class PhysiologicalProcess(BiologicalProcess):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Behavior(BiologicalProcess):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Death(BiologicalProcess):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Mixture():
    """
    The physical combination of two or more molecular entities in which the identities are retained and are mixed in
    the form of solutions, suspensions and colloids.
    """
    has_constituent: Optional[Union[Union[str, Curie, ChemicalSubstance], List[Union[str, Curie, ChemicalSubstance]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class ChemicalSubstance(MolecularEntity):
    """
    May be a chemical entity or a formulation with a chemical entity as active ingredient, or a complex material with
    multiple chemical entities as part
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    is_metabolite: Optional[Union[bool, Bool]] = None

@dataclass(config=PydanticConfig)
class Carbohydrate(ChemicalSubstance):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class ProcessedMaterial(ChemicalSubstance):
    """
    A chemical substance (often a mixture) processed for consumption for nutritional, medical or technical use.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    has_constituent: Optional[Union[Union[str, Curie, ChemicalSubstance], List[Union[str, Curie, ChemicalSubstance]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class Drug(MolecularEntity):
    """
    A substance intended for use in the diagnosis, cure, mitigation, treatment, or prevention of disease
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    has_constituent: Optional[Union[Union[str, Curie, ChemicalSubstance], List[Union[str, Curie, ChemicalSubstance]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class FoodComponent(ChemicalSubstance):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class EnvironmentalFoodContaminant(ChemicalSubstance):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class FoodAdditive(ChemicalSubstance):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Nutrient(ChemicalSubstance):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Macronutrient(Nutrient):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Micronutrient(Nutrient):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Vitamin(Micronutrient):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Food(MolecularEntity):
    """
    A substance consumed by a living organism as a source of nutrition
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    has_constituent: Optional[Union[Union[str, Curie, ChemicalSubstance], List[Union[str, Curie, ChemicalSubstance]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class Metabolite(ChemicalSubstance):
    """
    Any intermediate or product resulting from metabolism. Includes primary and secondary metabolites.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class OrganismAttribute(Attribute):
    """
    describes a characteristic of an organismal entity.
    """
    has_attribute_type: Union[str, OntologyClass] = None

@dataclass(config=PydanticConfig)
class PhenotypicQuality(OrganismAttribute):
    """
    A property of a phenotype
    """
    has_attribute_type: Union[str, OntologyClass] = None

@dataclass(config=PydanticConfig)
class Inheritance(OrganismAttribute):
    """
    The pattern or 'mode' in which a particular genetic trait or disorder is passed from one generation to the next,
    e.g. autosomal dominant, autosomal recessive, etc.
    """
    has_attribute_type: Union[str, OntologyClass] = None

@dataclass(config=PydanticConfig)
class OrganismalEntity(BiologicalEntity):
    """
    A named entity that is either a part of an organism, a whole organism, population or clade of organisms, excluding
    molecular entities
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    has_attribute: Optional[Union[Union[str, Attribute], List[Union[str, Attribute]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class LifeStage(OrganismalEntity):
    """
    A stage of development or growth of an organism, including post-natal adult stages
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    in_taxon: Optional[Union[Union[str, Curie, OrganismTaxon], List[Union[str, Curie, OrganismTaxon]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class IndividualOrganism(OrganismalEntity):
    """
    An instance of an organism. For example, Richard Nixon, Charles Darwin, my pet cat. Example ID:
    ORCID:0000-0002-5355-2576
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    in_taxon: Optional[Union[Union[str, Curie, OrganismTaxon], List[Union[str, Curie, OrganismTaxon]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class PopulationOfIndividualOrganisms(OrganismalEntity):
    """
    A collection of individuals from the same taxonomic class distinguished by one or more characteristics.
    Characteristics can include, but are not limited to, shared geographic location, genetics, phenotypes [Alliance
    for Genome Resources]
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    in_taxon: Optional[Union[Union[str, Curie, OrganismTaxon], List[Union[str, Curie, OrganismTaxon]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class StudyPopulation(PopulationOfIndividualOrganisms):
    """
    A group of people banded together or treated as a group as participants in a research study.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class DiseaseOrPhenotypicFeature(BiologicalEntity):
    """
    Either one of a disease or an individual phenotypic feature. Some knowledge resources such as Monarch treat these
    as distinct, others such as MESH conflate.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    in_taxon: Optional[Union[Union[str, Curie, OrganismTaxon], List[Union[str, Curie, OrganismTaxon]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class Disease(DiseaseOrPhenotypicFeature):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class PhenotypicFeature(DiseaseOrPhenotypicFeature):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class BehavioralFeature(PhenotypicFeature):
    """
    A phenotypic feature which is behavioral in nature.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class AnatomicalEntity(OrganismalEntity):
    """
    A subcellular location, cell type or gross anatomical part
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    in_taxon: Optional[Union[Union[str, Curie, OrganismTaxon], List[Union[str, Curie, OrganismTaxon]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class CellularComponent(AnatomicalEntity):
    """
    A location in or around a cell
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Cell(AnatomicalEntity):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class CellLine(OrganismalEntity):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class GrossAnatomicalStructure(AnatomicalEntity):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class MacromolecularMachineMixin():
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
    synonym: Optional[Union[Union[str, LabelType], List[Union[str, LabelType]]]] = field(default_factory=list)
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
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    has_biological_sequence: Optional[Union[str, BiologicalSequence]] = None

@dataclass(config=PydanticConfig)
class Gene(GenomicEntity):
    """
    A region (or regions) that includes all of the sequence elements necessary to encode a functional transcript. A
    gene locus may include regulatory regions, transcribed regions and/or other functional sequence regions.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    symbol: Optional[str] = None
    synonym: Optional[Union[Union[str, LabelType], List[Union[str, LabelType]]]] = field(default_factory=list)
    xref: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class Genome(GenomicEntity):
    """
    A genome is the sum of genetic material within a cell or virion.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Exon(GenomicEntity):
    """
    A region of the transcript sequence within a gene which is not removed from the primary RNA transcript by RNA
    splicing.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Transcript(GenomicEntity):
    """
    An RNA synthesized on a DNA or RNA template by an RNA polymerase.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class CodingSequence(GenomicEntity):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Protein(GenomicEntity):
    """
    A gene product that is composed of a chain of amino acid sequences and is produced by ribosome-mediated
    translation of mRNA
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    synonym: Optional[Union[Union[str, LabelType], List[Union[str, LabelType]]]] = field(default_factory=list)
    xref: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class ProteinIsoform(Protein):
    """
    Represents a protein that is a specific isoform of the canonical or reference protein. See
    https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4114032/
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class RNAProduct(Transcript):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    synonym: Optional[Union[Union[str, LabelType], List[Union[str, LabelType]]]] = field(default_factory=list)
    xref: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class RNAProductIsoform(RNAProduct):
    """
    Represents a protein that is a specific isoform of the canonical or reference RNA
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class NoncodingRNAProduct(RNAProduct):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class MicroRNA(NoncodingRNAProduct):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class SiRNA(NoncodingRNAProduct):
    """
    A small RNA molecule that is the product of a longer exogenous or endogenous dsRNA, which is either a bimolecular
    duplex or very long hairpin, processed (via the Dicer pathway) such that numerous siRNAs accumulate from both
    strands of the dsRNA. SRNAs trigger the cleavage of their target molecules.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class GeneGroupingMixin():
    """
    any grouping of multiple genes or gene products
    """
    has_gene_or_gene_product: Optional[Union[Union[str, Curie, Gene], List[Union[str, Curie, Gene]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class GeneFamily(MolecularEntity):
    """
    any grouping of multiple genes or gene products related by common descent
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    has_gene_or_gene_product: Optional[Union[Union[str, Curie, Gene], List[Union[str, Curie, Gene]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class Zygosity(Attribute):
    has_attribute_type: Union[str, OntologyClass] = None

@dataclass(config=PydanticConfig)
class Genotype(GenomicEntity):
    """
    An information content entity that describes a genome by specifying the total variation in genomic sequence and/or
    gene expression, relative to some established background
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    has_zygosity: Optional[Union[str, Zygosity]] = None

@dataclass(config=PydanticConfig)
class Haplotype(GenomicEntity):
    """
    A set of zero or more Alleles on a single instance of a Sequence[VMC]
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class SequenceVariant(GenomicEntity):
    """
    An allele that varies in its sequence from what is considered the reference allele at that locus.
    """
    id: Union[str, Curie, SequenceVariant] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    has_gene: Optional[Union[Union[str, Curie, Gene], List[Union[str, Curie, Gene]]]] = field(default_factory=list)
    has_biological_sequence: Optional[Union[str, BiologicalSequence]] = None

@dataclass(config=PydanticConfig)
class Snv(SequenceVariant):
    """
    SNVs are single nucleotide positions in genomic DNA at which different sequence alternatives exist
    """
    id: Union[str, Curie, Snv] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class ReagentTargetedGene(GenomicEntity):
    """
    A gene altered in its expression level in the context of some experiment as a result of being targeted by
    gene-knockdown reagent(s) such as a morpholino or RNAi.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class ClinicalAttribute(Attribute):
    """
    Attributes relating to a clinical manifestation
    """
    has_attribute_type: Union[str, OntologyClass] = None

@dataclass(config=PydanticConfig)
class ClinicalMeasurement(ClinicalAttribute):
    """
    A clinical measurement is a special kind of attribute which results from a laboratory observation from a subject
    individual or sample. Measurements can be connected to their subject by the 'has attribute' slot.
    """
    has_attribute_type: Union[str, OntologyClass] = None

@dataclass(config=PydanticConfig)
class ClinicalModifier(ClinicalAttribute):
    """
    Used to characterize and specify the phenotypic abnormalities defined in the phenotypic abnormality sub-ontology,
    with respect to severity, laterality, and other aspects
    """
    has_attribute_type: Union[str, OntologyClass] = None

@dataclass(config=PydanticConfig)
class ClinicalCourse(ClinicalAttribute):
    """
    The course a disease typically takes from its onset, progression in time, and eventual resolution or death of the
    affected individual
    """
    has_attribute_type: Union[str, OntologyClass] = None

@dataclass(config=PydanticConfig)
class Onset(ClinicalCourse):
    """
    The age group in which (disease) symptom manifestations appear
    """
    has_attribute_type: Union[str, OntologyClass] = None

@dataclass(config=PydanticConfig)
class ClinicalEntity(NamedThing):
    """
    Any entity or process that exists in the clinical domain and outside the biological realm. Diseases are placed
    under biological entities
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class ClinicalTrial(ClinicalEntity):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class ClinicalIntervention(ClinicalEntity):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class ClinicalFinding(PhenotypicFeature):
    """
    this category is currently considered broad enough to tag clinical lab measurements and other biological
    attributes taken as 'clinical traits' with some statistical score, for example, a p value in genetic associations.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    has_attribute: Optional[Union[Union[str, ClinicalAttribute], List[Union[str, ClinicalAttribute]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class Hospitalization(ClinicalIntervention):
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class SocioeconomicAttribute(Attribute):
    """
    Attributes relating to a socioeconomic manifestation
    """
    has_attribute_type: Union[str, OntologyClass] = None

@dataclass(config=PydanticConfig)
class Case(IndividualOrganism):
    """
    An individual (human) organism that has a patient role in some clinical context.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Cohort(StudyPopulation):
    """
    A group of people banded together or treated as a group who share common characteristics. A cohort 'study' is a
    particular form of longitudinal study that samples a cohort, performing a cross-section at intervals through time.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class ExposureEvent():
    """
    A (possibly time bounded) incidence of a feature of the environment of an organism that influences one or more
    phenotypic features of that organism, potentially mediated by genes
    """
    timepoint: Optional[Union[str, TimeType]] = None

@dataclass(config=PydanticConfig)
class GenomicBackgroundExposure(GenomicEntity):
    """
    A genomic background exposure is where an individual's specific genomic background of genes, sequence variants or
    other pre-existing genomic conditions constitute a kind of 'exposure' to the organism, leading to or influencing
    an outcome.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    timepoint: Optional[Union[str, TimeType]] = None
    has_gene_or_gene_product: Optional[Union[Union[str, Curie, Gene], List[Union[str, Curie, Gene]]]] = field(default_factory=list)

class PathologicalEntityMixin():
    """
    A pathological (abnormal) structure or process.
    """

@dataclass(config=PydanticConfig)
class PathologicalProcess(BiologicalProcess):
    """
    A biologic function or a process having an abnormal or deleterious effect at the subcellular, cellular,
    multicellular, or organismal level.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class PathologicalProcessExposure(PathologicalProcess):
    """
    A pathological process, when viewed as an exposure, representing an precondition, leading to or influencing an
    outcome, e.g. autoimmunity leading to disease.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    timepoint: Optional[Union[str, TimeType]] = None

@dataclass(config=PydanticConfig)
class PathologicalAnatomicalStructure(AnatomicalEntity):
    """
    An anatomical structure with the potential of have an abnormal or deleterious effect at the subcellular, cellular,
    multicellular, or organismal level.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class PathologicalAnatomicalExposure(PathologicalAnatomicalStructure):
    """
    An abnormal anatomical structure, when viewed as an exposure, representing an precondition, leading to or
    influencing an outcome, e.g. thrombosis leading to an ischemic disease outcome.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    timepoint: Optional[Union[str, TimeType]] = None

@dataclass(config=PydanticConfig)
class DiseaseOrPhenotypicFeatureExposure(DiseaseOrPhenotypicFeature):
    """
    A disease or phenotypic feature state, when viewed as an exposure, represents an precondition, leading to or
    influencing an outcome, e.g. HIV predisposing an individual to infections; a relative deficiency of skin
    pigmentation predisposing an individual to skin cancer.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    timepoint: Optional[Union[str, TimeType]] = None

@dataclass(config=PydanticConfig)
class ChemicalExposure(ChemicalSubstance):
    """
    A chemical exposure is an intake of a particular chemical substance, other than a drug.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    timepoint: Optional[Union[str, TimeType]] = None

@dataclass(config=PydanticConfig)
class ComplexChemicalExposure(ChemicalExposure):
    """
    A complex chemical exposure is an intake of a chemical mixture (e.g. gasoline), other than a drug.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    has_constituent: Optional[Union[Union[str, Curie, ChemicalSubstance], List[Union[str, Curie, ChemicalSubstance]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class DrugExposure(Drug):
    """
    A drug exposure is an intake of a particular drug.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    timepoint: Optional[Union[str, TimeType]] = None

@dataclass(config=PydanticConfig)
class DrugToGeneInteractionExposure(DrugExposure):
    """
    drug to gene interaction exposure is a drug exposure is where the interactions of the drug with specific genes are
    known to constitute an 'exposure' to the organism, leading to or influencing an outcome.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    has_gene_or_gene_product: Optional[Union[Union[str, Curie, Gene], List[Union[str, Curie, Gene]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class Treatment(NamedThing):
    """
    A treatment is targeted at a disease or phenotype and may involve multiple drug 'exposures', medical devices
    and/or procedures
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    has_drug: Optional[Union[Union[str, Curie, Drug], List[Union[str, Curie, Drug]]]] = field(default_factory=list)
    has_device: Optional[Union[Union[str, Curie, Device], List[Union[str, Curie, Device]]]] = field(default_factory=list)
    has_procedure: Optional[Union[Union[str, Curie, Procedure], List[Union[str, Curie, Procedure]]]] = field(default_factory=list)
    timepoint: Optional[Union[str, TimeType]] = None

@dataclass(config=PydanticConfig)
class BioticExposure(OrganismTaxon):
    """
    An external biotic exposure is an intake of (sometimes pathological) biological organisms (including viruses).
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    timepoint: Optional[Union[str, TimeType]] = None

@dataclass(config=PydanticConfig)
class GeographicExposure(GeographicLocation):
    """
    A geographic exposure is a factor relating to geographic proximity to some impactful entity.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    timepoint: Optional[Union[str, TimeType]] = None

@dataclass(config=PydanticConfig)
class EnvironmentalExposure(EnvironmentalProcess):
    """
    A environmental exposure is a factor relating to abiotic processes in the environment including sunlight (UV-B),
    atmospheric (heat, cold, general pollution) and water-born contaminants.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    timepoint: Optional[Union[str, TimeType]] = None

@dataclass(config=PydanticConfig)
class BehavioralExposure(Behavior):
    """
    A behavioral exposure is a factor relating to behavior impacting an individual.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    timepoint: Optional[Union[str, TimeType]] = None

@dataclass(config=PydanticConfig)
class SocioeconomicExposure(Behavior):
    """
    A socioeconomic exposure is a factor relating to social and financial status of an affected individual (e.g.
    poverty).
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None
    has_attribute: Union[Union[str, SocioeconomicAttribute], List[Union[str, SocioeconomicAttribute]]] = None
    timepoint: Optional[Union[str, TimeType]] = None

class Outcome():
    """
    An entity that has the role of being the consequence of an exposure event. This is an abstract mixin grouping of
    various categories of possible biological or non-biological (e.g. clinical) outcomes.
    """

@dataclass(config=PydanticConfig)
class PathologicalProcessOutcome(PathologicalProcess):
    """
    An outcome resulting from an exposure event which is the manifestation of a pathological process.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class PathologicalAnatomicalOutcome(PathologicalAnatomicalStructure):
    """
    An outcome resulting from an exposure event which is the manifestation of an abnormal anatomical structure.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class DiseaseOrPhenotypicFeatureOutcome(DiseaseOrPhenotypicFeature):
    """
    Physiological outcomes resulting from an exposure event which is the manifestation of a disease or other
    characteristic phenotype.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class BehavioralOutcome(Behavior):
    """
    An outcome resulting from an exposure event which is the manifestation of human behavior.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class HospitalizationOutcome(Hospitalization):
    """
    An outcome resulting from an exposure event which is the increased manifestation of acute (e.g. emergency room
    visit) or chronic (inpatient) hospitalization.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class MortalityOutcome(Death):
    """
    An outcome of death from resulting from an exposure event.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class EpidemiologicalOutcome(BiologicalEntity):
    """
    An epidemiological outcome, such as societal disease burden, resulting from an exposure event.
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class SocioeconomicOutcome(Behavior):
    """
    An general social or economic outcome, such as healthcare costs, utilization, etc., resulting from an exposure
    event
    """
    id: Union[str, Curie] = None
    category: Union[Union[str, Curie, NamedThing], List[Union[str, Curie, NamedThing]]] = None

@dataclass(config=PydanticConfig)
class Association(Entity):
    """
    A typed association between two entities, supported by evidence
    """
    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    negated: Optional[Union[bool, Bool]] = None
    qualifiers: Optional[Union[Union[str, OntologyClass], List[Union[str, OntologyClass]]]] = field(default_factory=list)
    publications: Optional[Union[Union[str, Curie, Publication], List[Union[str, Curie, Publication]]]] = field(default_factory=list)
    type: Optional[str] = None
    category: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class ContributorAssociation(Association):
    """
    Any association between an entity (such as a publication) and various agents that contribute to its realisation
    """
    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, InformationContentEntity] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, Agent] = None
    qualifiers: Optional[Union[Union[str, OntologyClass], List[Union[str, OntologyClass]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class GenotypeToGenotypePartAssociation(Association):
    """
    Any association between one genotype and a genotypic entity that is a sub-component of it
    """
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
    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, GeneOrGeneProduct] = None
    object: Union[str, GeneOrGeneProduct] = None
    predicate: Union[str, Curie] = None

@dataclass(config=PydanticConfig)
class GeneExpressionMixin():
    """
    Observed gene expression intensity, context (site, stage) and associated phenotypic status within which the
    expression occurs.
    """
    quantifier_qualifier: Optional[Union[str, OntologyClass]] = None
    expression_site: Optional[Union[str, Curie, AnatomicalEntity]] = None
    stage_qualifier: Optional[Union[str, Curie, LifeStage]] = None
    phenotypic_state: Optional[Union[str, Curie, DiseaseOrPhenotypicFeature]] = None

@dataclass(config=PydanticConfig)
class GeneToGeneCoexpressionAssociation(GeneToGeneAssociation):
    """
    Indicates that two genes are co-expressed, generally under the same conditions.
    """
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
    id: Union[str, Curie, PairwiseMolecularInteraction] = None
    subject: Union[str, Curie, MolecularEntity] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    object: Union[str, Curie, MolecularEntity] = None
    interacting_molecules_category: Optional[Union[str, OntologyClass]] = None

@dataclass(config=PydanticConfig)
class CellLineToEntityAssociationMixin():
    """
    An relationship between a cell line and another entity
    """
    subject: Union[str, Curie, CellLine] = None

@dataclass(config=PydanticConfig)
class CellLineToDiseaseOrPhenotypicFeatureAssociation(Association):
    """
    An relationship between a cell line and a disease or a phenotype, where the cell line is derived from an
    individual with that disease or phenotype.
    """
    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, DiseaseOrPhenotypicFeature] = None

@dataclass(config=PydanticConfig)
class MolecularEntityToEntityAssociationMixin():
    """
    An interaction between a molecular entity and another entity
    """
    subject: Union[str, Curie, MolecularEntity] = None

@dataclass(config=PydanticConfig)
class DrugToEntityAssociationMixin(MolecularEntityToEntityAssociationMixin):
    """
    An interaction between a drug and another entity
    """
    subject: Union[str, Curie, Drug] = None

@dataclass(config=PydanticConfig)
class ChemicalToEntityAssociationMixin(MolecularEntityToEntityAssociationMixin):
    """
    An interaction between a chemical entity and another entity
    """
    subject: Union[str, Curie, ChemicalSubstance] = None

@dataclass(config=PydanticConfig)
class CaseToEntityAssociationMixin():
    """
    An abstract association for use where the case is the subject
    """
    subject: Union[str, Curie, Case] = None

@dataclass(config=PydanticConfig)
class ChemicalToChemicalAssociation(Association):
    """
    A relationship between two chemical entities. This can encompass actual interactions as well as temporal causal
    edges, e.g. one chemical converted to another.
    """
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
    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, ChemicalSubstance] = None
    object: Union[str, Curie, ChemicalSubstance] = None
    predicate: Union[str, Curie] = None
    catalyst_qualifier: Optional[Union[Union[str, MacromolecularMachineMixin], List[Union[str, MacromolecularMachineMixin]]]] = field(default_factory=list)

@dataclass(config=PydanticConfig)
class ChemicalToDiseaseOrPhenotypicFeatureAssociation(Association):
    """
    An interaction between a chemical entity and a phenotype or disease, where the presence of the chemical gives rise
    to or exacerbates the phenotype.
    """
    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    object: Union[str, Curie, DiseaseOrPhenotypicFeature] = None

@dataclass(config=PydanticConfig)
class ChemicalToPathwayAssociation(Association):
    """
    An interaction between a chemical entity and a biological process or pathway.
    """
    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    object: Union[str, Curie, Pathway] = None

@dataclass(config=PydanticConfig)
class ChemicalToGeneAssociation(Association):
    """
    An interaction between a chemical entity and a gene or gene product.
    """
    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    object: Union[str, GeneOrGeneProduct] = None

@dataclass(config=PydanticConfig)
class DrugToGeneAssociation(Association):
    """
    An interaction between a drug and a gene or gene product.
    """
    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    object: Union[str, GeneOrGeneProduct] = None

@dataclass(config=PydanticConfig)
class MaterialSampleToEntityAssociationMixin():
    """
    An association between a material sample and something.
    """
    subject: Union[str, Curie, MaterialSample] = None

@dataclass(config=PydanticConfig)
class MaterialSampleDerivationAssociation(Association):
    """
    An association between a material sample and the material entity from which it is derived.
    """
    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, MaterialSample] = None
    object: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None

@dataclass(config=PydanticConfig)
class MaterialSampleToDiseaseOrPhenotypicFeatureAssociation(Association):
    """
    An association between a material sample and a disease or phenotype.
    """
    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None

@dataclass(config=PydanticConfig)
class DiseaseToEntityAssociationMixin():
    subject: Union[str, Curie, Disease] = None

@dataclass(config=PydanticConfig)
class EntityToExposureEventAssociationMixin():
    """
    An association between some entity and an exposure event.
    """
    object: Union[str, ExposureEvent] = None

@dataclass(config=PydanticConfig)
class DiseaseToExposureEventAssociation(Association):
    """
    An association between an exposure event and a disease.
    """
    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None

@dataclass(config=PydanticConfig)
class ExposureEventToEntityAssociationMixin():
    """
    An association between some exposure event and some entity.
    """
    subject: Union[str, ExposureEvent] = None

@dataclass(config=PydanticConfig)
class EntityToOutcomeAssociationMixin():
    """
    An association between some entity and an outcome
    """
    object: Union[str, Outcome] = None

@dataclass(config=PydanticConfig)
class ExposureEventToOutcomeAssociation(Association):
    """
    An association between an exposure event and an outcome.
    """
    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    has_population_context: Optional[Union[str, Curie, PopulationOfIndividualOrganisms]] = None
    has_temporal_context: Optional[Union[str, TimeType]] = None

@dataclass(config=PydanticConfig)
class FrequencyQualifierMixin():
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
    object: Union[str, Curie, PhenotypicFeature] = None
    sex_qualifier: Optional[Union[str, BiologicalSex]] = None
    description: Optional[Union[str, NarrativeText]] = None

@dataclass(config=PydanticConfig)
class EntityToDiseaseAssociationMixin(EntityToFeatureOrDiseaseQualifiersMixin):
    """
    mixin class for any association whose object (target node) is a disease
    """
    object: Union[str, Curie, Disease] = None

@dataclass(config=PydanticConfig)
class DiseaseOrPhenotypicFeatureToEntityAssociationMixin():
    subject: Union[str, Curie, DiseaseOrPhenotypicFeature] = None

@dataclass(config=PydanticConfig)
class DiseaseOrPhenotypicFeatureAssociationToLocationAssociation(Association):
    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    object: Union[str, Curie, AnatomicalEntity] = None

@dataclass(config=PydanticConfig)
class DiseaseOrPhenotypicFeatureToLocationAssociation(Association):
    """
    An association between either a disease or a phenotypic feature and an anatomical entity, where the
    disease/feature manifests in that site.
    """
    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    object: Union[str, Curie, AnatomicalEntity] = None

@dataclass(config=PydanticConfig)
class EntityToDiseaseOrPhenotypicFeatureAssociationMixin():
    object: Union[str, Curie, DiseaseOrPhenotypicFeature] = None

@dataclass(config=PydanticConfig)
class GenotypeToEntityAssociationMixin():
    subject: Union[str, Curie, Genotype] = None

@dataclass(config=PydanticConfig)
class GenotypeToPhenotypicFeatureAssociation(Association):
    """
    Any association between one genotype and a phenotypic feature, where having the genotype confers the phenotype,
    either in isolation or through environment
    """
    id: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    subject: Union[str, Curie, Genotype] = None
    sex_qualifier: Optional[Union[str, BiologicalSex]] = None

@dataclass(config=PydanticConfig)
class ExposureEventToPhenotypicFeatureAssociation(Association):
    """
    Any association between an environment and a phenotypic feature, where being in the environment influences the
    phenotype.
    """
    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    subject: Union[str, ExposureEvent] = None
    sex_qualifier: Optional[Union[str, BiologicalSex]] = None

@dataclass(config=PydanticConfig)
class DiseaseToPhenotypicFeatureAssociation(Association):
    """
    An association between a disease and a phenotypic feature in which the phenotypic feature is associated with the
    disease in some way.
    """
    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    sex_qualifier: Optional[Union[str, BiologicalSex]] = None

@dataclass(config=PydanticConfig)
class CaseToPhenotypicFeatureAssociation(Association):
    """
    An association between a case (e.g. individual patient) and a phenotypic feature in which the individual has or
    has had the phenotype.
    """
    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    sex_qualifier: Optional[Union[str, BiologicalSex]] = None

@dataclass(config=PydanticConfig)
class BehaviorToBehavioralFeatureAssociation(Association):
    """
    An association between an aggregate behavior and a behavioral feature manifested by the individual exhibited or
    has exhibited the behavior.
    """
    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, Behavior] = None
    object: Union[str, Curie, BehavioralFeature] = None
    sex_qualifier: Optional[Union[str, BiologicalSex]] = None

@dataclass(config=PydanticConfig)
class GeneToEntityAssociationMixin():
    subject: Union[str, GeneOrGeneProduct] = None

@dataclass(config=PydanticConfig)
class VariantToEntityAssociationMixin():
    subject: Union[str, Curie, SequenceVariant] = None

@dataclass(config=PydanticConfig)
class GeneToPhenotypicFeatureAssociation(Association):
    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    subject: Union[str, GeneOrGeneProduct] = None
    sex_qualifier: Optional[Union[str, BiologicalSex]] = None

@dataclass(config=PydanticConfig)
class GeneToDiseaseAssociation(Association):
    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    subject: Union[str, GeneOrGeneProduct] = None

@dataclass(config=PydanticConfig)
class VariantToGeneAssociation(Association):
    """
    An association between a variant and a gene, where the variant has a genetic association with the gene (i.e. is in
    linkage disequilibrium)
    """
    id: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    object: Union[str, Curie, Gene] = None
    predicate: Union[str, Curie] = None

@dataclass(config=PydanticConfig)
class VariantToGeneExpressionAssociation(VariantToGeneAssociation):
    """
    An association between a variant and expression of a gene (i.e. e-QTL)
    """
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
class VariantToPopulationAssociation(Association):
    """
    An association between a variant and a population, where the variant has particular frequency in the population
    """
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
    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, PopulationOfIndividualOrganisms] = None
    object: Union[str, Curie, PopulationOfIndividualOrganisms] = None
    predicate: Union[str, Curie] = None

@dataclass(config=PydanticConfig)
class VariantToPhenotypicFeatureAssociation(Association):
    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, SequenceVariant] = None
    sex_qualifier: Optional[Union[str, BiologicalSex]] = None

@dataclass(config=PydanticConfig)
class VariantToDiseaseAssociation(Association):
    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None

@dataclass(config=PydanticConfig)
class GenotypeToDiseaseAssociation(Association):
    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None

@dataclass(config=PydanticConfig)
class ModelToDiseaseAssociationMixin():
    """
    This mixin is used for any association class for which the subject (source node) plays the role of a 'model', in
    that it recapitulates some features of the disease in a way that is useful for studying the disease outside a
    patient carrying the disease
    """
    subject: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None

@dataclass(config=PydanticConfig)
class GeneAsAModelOfDiseaseAssociation(GeneToDiseaseAssociation):
    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    subject: Union[str, GeneOrGeneProduct] = None

@dataclass(config=PydanticConfig)
class VariantAsAModelOfDiseaseAssociation(VariantToDiseaseAssociation):
    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    subject: Union[str, Curie, SequenceVariant] = None

@dataclass(config=PydanticConfig)
class GenotypeAsAModelOfDiseaseAssociation(GenotypeToDiseaseAssociation):
    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    subject: Union[str, Curie, Genotype] = None

@dataclass(config=PydanticConfig)
class CellLineAsAModelOfDiseaseAssociation(CellLineToDiseaseOrPhenotypicFeatureAssociation):
    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, CellLine] = None

@dataclass(config=PydanticConfig)
class OrganismalEntityAsAModelOfDiseaseAssociation(Association):
    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    object: Union[str, Curie, NamedThing] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, OrganismalEntity] = None

@dataclass(config=PydanticConfig)
class GeneHasVariantThatContributesToDiseaseAssociation(GeneToDiseaseAssociation):
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
    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, MacromolecularMachineMixin] = None
    object: Union[str, GeneOntologyClass] = None

@dataclass(config=PydanticConfig)
class MacromolecularMachineToEntityAssociationMixin():
    """
    an association which has a macromolecular machine mixin as a subject
    """
    subject: Union[str, Curie, NamedThing] = None

@dataclass(config=PydanticConfig)
class MacromolecularMachineToMolecularActivityAssociation(FunctionalAssociation):
    """
    A functional association between a macromolecular machine (gene, gene product or complex) and a molecular activity
    (as represented in the GO molecular function branch), where the entity carries out the activity, or contributes to
    its execution.
    """
    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, MacromolecularMachineMixin] = None
    object: Union[str, Curie, MolecularActivity] = None

@dataclass(config=PydanticConfig)
class MacromolecularMachineToBiologicalProcessAssociation(FunctionalAssociation):
    """
    A functional association between a macromolecular machine (gene, gene product or complex) and a biological process
    or pathway (as represented in the GO biological process branch), where the entity carries out some part of the
    process, regulates it, or acts upstream of it.
    """
    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, MacromolecularMachineMixin] = None
    object: Union[str, Curie, BiologicalProcess] = None

@dataclass(config=PydanticConfig)
class MacromolecularMachineToCellularComponentAssociation(FunctionalAssociation):
    """
    A functional association between a macromolecular machine (gene, gene product or complex) and a cellular component
    (as represented in the GO cellular component branch), where the entity carries out its function in the cellular
    component.
    """
    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, MacromolecularMachineMixin] = None
    object: Union[str, Curie, CellularComponent] = None

@dataclass(config=PydanticConfig)
class GeneToGoTermAssociation(FunctionalAssociation):
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
    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    subject: Union[str, GeneOrGeneProduct] = None
    object: Union[str, GeneOrGeneProduct] = None

@dataclass(config=PydanticConfig)
class AnatomicalEntityToAnatomicalEntityAssociation(Association):
    id: Union[str, Curie] = None
    predicate: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, AnatomicalEntity] = None
    object: Union[str, Curie, AnatomicalEntity] = None

@dataclass(config=PydanticConfig)
class AnatomicalEntityToAnatomicalEntityPartOfAssociation(AnatomicalEntityToAnatomicalEntityAssociation):
    """
    A relationship between two anatomical entities where the relationship is mereological, i.e the two entities are
    related by parthood. This includes relationships between cellular components and cells, between cells and tissues,
    tissues and whole organisms
    """
    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, AnatomicalEntity] = None
    object: Union[str, Curie, AnatomicalEntity] = None
    predicate: Union[str, Curie] = None

@dataclass(config=PydanticConfig)
class AnatomicalEntityToAnatomicalEntityOntogenicAssociation(AnatomicalEntityToAnatomicalEntityAssociation):
    """
    A relationship between two anatomical entities where the relationship is ontogenic, i.e. the two entities are
    related by development. A number of different relationship types can be used to specify the precise nature of the
    relationship.
    """
    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, AnatomicalEntity] = None
    object: Union[str, Curie, AnatomicalEntity] = None
    predicate: Union[str, Curie] = None

@dataclass(config=PydanticConfig)
class OrganismTaxonToEntityAssociation():
    """
    An association between an organism taxon and another entity
    """
    subject: Union[str, Curie, OrganismTaxon] = None

@dataclass(config=PydanticConfig)
class OrganismTaxonToOrganismTaxonAssociation(Association):
    """
    A relationship between two organism taxon nodes
    """
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
    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, OrganismTaxon] = None
    object: Union[str, Curie, OrganismTaxon] = None
    predicate: Union[str, Curie] = None
    associated_environmental_context: Optional[str] = None

@dataclass(config=PydanticConfig)
class OrganismTaxonToEnvironmentAssociation(Association):
    id: Union[str, Curie] = None
    relation: Union[str, Curie] = None
    subject: Union[str, Curie, OrganismTaxon] = None
    object: Union[str, Curie, NamedThing] = None
    predicate: Union[str, Curie] = None

