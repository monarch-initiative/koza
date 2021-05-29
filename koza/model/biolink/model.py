# Auto generated from biolink-model.yaml by pydanticgen.py version: 0.9.0
# Generation date: 2021-05-28 20:26
# Schema: Biolink-Model
#
# id: https://w3id.org/biolink/biolink-model
# description: Entity and association taxonomy and datamodel for life-sciences data
# license: https://creativecommons.org/publicdomain/zero/1.0/

import datetime
import inspect
import logging
from collections import namedtuple
from dataclasses import field
from typing import Any, ClassVar, List, Optional, Union

from pydantic import constr, validator
from pydantic.dataclasses import dataclass

LOG = logging.getLogger(__name__)

metamodel_version = "1.7.0"

# Type Aliases
Unit = Union[int, float]
LabelType = str
IriType = constr(regex=r'^http')
Curie = constr(regex=r'^[a-zA-Z_]?[a-zA-Z_0-9-]*:[A-Za-z0-9_][A-Za-z0-9_.-]*[A-Za-z0-9_]*$')
NarrativeText = str
XSDDate = datetime.date
TimeType = datetime.time
SymbolType = str
FrequencyValue = str
PercentageFrequencyValue = float
BiologicalSequence = str
Quotient = float

# Namespaces

valid_prefix = [
    "APO",
    "Aeolus",
    "BIOGRID",
    "BIOSAMPLE",
    "BSPO",
    "CAID",
    "CAS",
    "CATH",
    "CATH_SUPERFAMILY",
    "CDD",
    "CHADO",
    "CHEBI",
    "CHEMBL_COMPOUND",
    "CHEMBL_MECHANISM",
    "CHEMBL_TARGET",
    "CID",
    "CL",
    "CLINVAR",
    "CLO",
    "COAR_RESOURCE",
    "CPT",
    "CTD",
    "ChemBank",
    "ClinVarVariant",
    "DBSNP",
    "DGIdb",
    "DOID",
    "DRUGBANK",
    "DrugCentral",
    "EC",
    "ECTO",
    "EDAM-DATA",
    "EDAM-FORMAT",
    "EDAM-OPERATION",
    "EDAM-TOPIC",
    "EFO",
    "EGGNOG",
    "ENSEMBL",
    "ExO",
    "FAO",
    "FB",
    "FBcv",
    "GAMMA",
    "GO",
    "GOLD_META",
    "GOP",
    "GOREL",
    "GSID",
    "GTEx",
    "GTOPDB",
    "HAMAP",
    "HANCESTRO",
    "HCPCS",
    "HGNC",
    "HGNC_FAMILY",
    "HMDB",
    "HP",
    "HsapDv",
    "ICD0",
    "ICD10",
    "ICD9",
    "INCHI",
    "INCHIKEY",
    "INO",
    "INTACT",
    "IUPHAR_FAMILY",
    "KEGG",
    "KEGG_BRITE",
    "KEGG_COMPOUND",
    "KEGG_DGROUP",
    "KEGG_DISEASE",
    "KEGG_DRUG",
    "KEGG_ENVIRON",
    "KEGG_ENZYME",
    "KEGG_GENE",
    "KEGG_GLYCAN",
    "KEGG_MODULE",
    "KEGG_ORTHOLOGY",
    "KEGG_RCLASS",
    "KEGG_REACTION",
    "LOINC",
    "MEDDRA",
    "MESH",
    "MGI",
    "MI",
    "MIR",
    "MONDO",
    "MP",
    "MSigDB",
    "MetaCyc",
    "NCBIGene",
    "NCBITaxon",
    "NCIT",
    "NDC",
    "NDDF",
    "NLMID",
    "OBAN",
    "OBOREL",
    "OIO",
    "OMIM",
    "ORCID",
    "ORPHA",
    "ORPHANET",
    "PANTHER_FAMILY",
    "PANTHER_PATHWAY",
    "PATO",
    "PATO-PROPERTY",
    "PDQ",
    "PFAM",
    "PHARMGKB_DRUG",
    "PHARMGKB_PATHWAYS",
    "PHAROS",
    "PIRSF",
    "PMID",
    "PO",
    "POMBASE",
    "PR",
    "PRINTS",
    "PRODOM",
    "PROSITE",
    "PUBCHEM_COMPOUND",
    "PUBCHEM_SUBSTANCE",
    "PathWhiz",
    "REACT",
    "REPODB",
    "RFAM",
    "RGD",
    "RHEA",
    "RNACENTRAL",
    "RO",
    "RTXKG1",
    "RXCUI",
    "RXNORM",
    "ResearchID",
    "SEMMEDDB",
    "SGD",
    "SIDER_DRUG",
    "SIO",
    "SMART",
    "SMPDB",
    "SNOMEDCT",
    "SNPEFF",
    "SUPFAM",
    "ScopusID",
    "TAXRANK",
    "TCDB",
    "TIGRFAM",
    "UBERGRAPH",
    "UBERON",
    "UBERON_CORE",
    "UMLS",
    "UMLSSC",
    "UMLSSG",
    "UMLSST",
    "UNII",
    "UNIPROT_ISOFORM",
    "UO",
    "UPHENO",
    "UniProtKB",
    "VANDF",
    "VMC",
    "WB",
    "WBPhenotype",
    "WBVocab",
    "WIKIDATA",
    "WIKIDATA_PROPERTY",
    "WIKIPATHWAYS",
    "WormBase",
    "ZFIN",
    "ZP",
    "alliancegenome",
    "biolink",
    "chembio",
    "dcat",
    "dct",
    "dictyBase",
    "doi",
    "fabio",
    "foaf",
    "foodb_compound",
    "gff3",
    "gpi",
    "gtpo",
    "hetio",
    "interpro",
    "isbn",
    "isni",
    "issn",
    "linkml",
    "medgen",
    "oboformat",
    "os",
    "pav",
    "prov",
    "qud",
    "rdf",
    "rdfs",
    "schema",
    "skos",
    "wgs",
    "xsd",
]


# Pydantic config and validators


class PydanticConfig:
    """
    Pydantic config
    https://pydantic-docs.helpmanual.io/usage/model_config/
    """

    validate_assignment = True
    validate_all = True
    underscore_attrs_are_private = True
    extra = 'forbid'
    arbitrary_types_allowed = True  # TODO re-evaluate this


def check_curie_prefix(cls, curie: Union[List, str, None]):
    if isinstance(curie, list):
        for cur in curie:
            prefix = cur.split(':')[0]
            if prefix not in valid_prefix:

                LOG.warning(f"{curie} prefix '{prefix}' not in curie map")
                if hasattr(cls, '_id_prefixes') and cls._id_prefixes:
                    LOG.warning(f"Consider one of {cls._id_prefixes}")
                else:
                    LOG.warning(
                        f"See https://biolink.github.io/biolink-model/context.jsonld "
                        f"for a list of valid curie prefixes"
                    )
    elif curie:
        prefix = curie.split(':')[0]
        if prefix not in valid_prefix:
            LOG.warning(f"{curie} prefix '{prefix}' not in curie map")
            if hasattr(cls, '_id_prefixes') and cls._id_prefixes:
                LOG.warning(f"Consider one of {cls._id_prefixes}")
            else:
                LOG.warning(
                    f"See https://biolink.github.io/biolink-model/context.jsonld "
                    f"for a list of valid curie prefixes"
                )


def convert_scalar_to_list_check_curies(cls, field: Any) -> List[str]:
    if not isinstance(field, list):
        field = [field]
    for feld in field:
        if isinstance(feld, str):
            check_curie_prefix(cls, feld)
    return field


def convert_scalar_to_list(field: Any) -> List[str]:
    if not isinstance(field, list):
        field = [field]
    return field


# Classes


@dataclass(config=PydanticConfig)
class OntologyClass:
    """
    a concept or class in an ontology, vocabulary or thesaurus. Note that nodes in a biolink compatible KG can be
    considered both instances of biolink classes, and OWL classes in their own right. In general you should not need
    to use this class directly. Instead, use the appropriate biolink class. For example, for the GO concept of
    endocytosis (GO:0006897), use bl:BiologicalProcess as the type.
    """

    # Class Variables
    _id_prefixes: ClassVar[List[str]] = ["MESH", "UMLS", "KEGG.BRITE"]


@dataclass(config=PydanticConfig)
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

    # Class Variables
    _category: ClassVar[str] = "QuantityValue"

    has_unit: Optional[Union[str, Unit]] = None
    has_numeric_value: Optional[float] = None


@dataclass(config=PydanticConfig)
class Attribute(Annotation, OntologyClass):
    """
    A property or characteristic of an entity. For example, an apple may have properties such as color, shape, age,
    crispiness. An environmental sample may have attributes such as depth, lat, long, material.
    """

    # Class Variables
    _category: ClassVar[str] = "Attribute"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]
    _id_prefixes: ClassVar[List[str]] = ["EDAM-DATA", "EDAM-FORMAT", "EDAM-OPERATION", "EDAM-TOPIC"]

    has_attribute_type: Union[str, OntologyClass] = None
    name: Optional[Union[str, LabelType]] = None
    has_quantitative_value: Optional[
        Union[Union[str, QuantityValue], List[Union[str, QuantityValue]]]
    ] = field(default_factory=list)
    has_qualitative_value: Optional[Curie] = None
    iri: Optional[IriType] = None
    source: Optional[Union[str, LabelType]] = None

    # Validators

    @validator('has_quantitative_value')
    def convert_has_quantitative_value_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)

    @validator('has_qualitative_value')
    def check_has_qualitative_value_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class BiologicalSex(Attribute):

    # Class Variables
    _category: ClassVar[str] = "BiologicalSex"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]


@dataclass(config=PydanticConfig)
class PhenotypicSex(BiologicalSex):
    """
    An attribute corresponding to the phenotypic sex of the individual, based upon the reproductive organs present.
    """

    # Class Variables
    _category: ClassVar[str] = "PhenotypicSex"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]


@dataclass(config=PydanticConfig)
class GenotypicSex(BiologicalSex):
    """
    An attribute corresponding to the genotypic sex of the individual, based upon genotypic composition of sex
    chromosomes.
    """

    # Class Variables
    _category: ClassVar[str] = "GenotypicSex"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]


@dataclass(config=PydanticConfig)
class SeverityValue(Attribute):
    """
    describes the severity of a phenotypic feature or disease
    """

    # Class Variables
    _category: ClassVar[str] = "SeverityValue"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]


@dataclass(config=PydanticConfig)
class RelationshipQuantifier:

    pass


@dataclass(config=PydanticConfig)
class SensitivityQuantifier(RelationshipQuantifier):

    pass


@dataclass(config=PydanticConfig)
class SpecificityQuantifier(RelationshipQuantifier):

    pass


@dataclass(config=PydanticConfig)
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


@dataclass(config=PydanticConfig)
class ChemicalOrDrugOrTreatment:

    pass


@dataclass(config=PydanticConfig)
class Entity:
    """
    Root Biolink Model class for all things and informational relationships, real or imagined.
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["id"]

    id: Curie = None
    iri: Optional[IriType] = None
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

    # Validators

    @validator('id')
    def check_id_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field

    @validator('category')
    def convert_category_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)

    @validator('provided_by')
    def convert_provided_by_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)

    @validator('has_attribute')
    def convert_has_attribute_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)

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

    # Class Variables
    _category: ClassVar[str] = "NamedThing"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    category: Union[Union[str, Curie], List[Union[str, Curie]]] = None

    # Validators

    @validator('category')
    def convert_category_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)


@dataclass(config=PydanticConfig)
class RelationshipType(OntologyClass):
    """
    An OWL property used as an edge label
    """

    # Class Variables
    _category: ClassVar[str] = "RelationshipType"


@dataclass(config=PydanticConfig)
class GeneOntologyClass(OntologyClass):
    """
    an ontology class that describes a functional aspect of a gene, gene prodoct or complex
    """


@dataclass(config=PydanticConfig)
class UnclassifiedOntologyClass(OntologyClass):
    """
    this is used for nodes that are taken from an ontology but are not typed using an existing biolink class
    """


@dataclass(config=PydanticConfig)
class TaxonomicRank(OntologyClass):
    """
    A descriptor for the rank within a taxonomic classification. Example instance: TAXRANK:0000017 (kingdom)
    """

    # Class Variables
    _category: ClassVar[str] = "TaxonomicRank"
    _id_prefixes: ClassVar[List[str]] = ["TAXRANK"]


@dataclass(config=PydanticConfig)
class OrganismTaxon(NamedThing):
    """
    A classification of a set of organisms. Example instances: NCBITaxon:9606 (Homo sapiens), NCBITaxon:2 (Bacteria).
    Can also be used to represent strains or subspecies.
    """

    # Class Variables
    _category: ClassVar[str] = "OrganismTaxon"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["NCBITaxon", "MESH"]

    has_taxonomic_rank: Optional[Union[str, TaxonomicRank]] = None
    subclass_of: Optional[Union[Curie, List[Curie]]] = field(default_factory=list)

    # Validators

    @validator('subclass_of')
    def convert_subclass_of_to_list_check_curies(cls, field):
        return convert_scalar_to_list_check_curies(cls, field)


@dataclass(config=PydanticConfig)
class AdministrativeEntity(NamedThing):

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Agent(AdministrativeEntity):
    """
    person, group, organization or project that provides a piece of information (i.e. a knowledge association)
    """

    # Class Variables
    _category: ClassVar[str] = "Agent"
    _required_attributes: ClassVar[List[str]] = ["category", "id"]
    _id_prefixes: ClassVar[List[str]] = ["isbn", "ORCID", "ScopusID", "ResearchID", "GSID", "isni"]

    id: Curie = None
    affiliation: Optional[Union[Curie, List[Curie]]] = field(default_factory=list)
    address: Optional[str] = None
    name: Optional[Union[str, LabelType]] = None

    # Validators

    @validator('affiliation')
    def convert_affiliation_to_list_check_curies(cls, field):
        return convert_scalar_to_list_check_curies(cls, field)

    @validator('id')
    def check_id_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class InformationContentEntity(NamedThing):
    """
    a piece of information that typically describes some topic of discourse or is used as support.
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["doi"]

    license: Optional[str] = None
    rights: Optional[str] = None
    format: Optional[str] = None
    creation_date: Optional[Union[str, XSDDate]] = None


@dataclass(config=PydanticConfig)
class Dataset(InformationContentEntity):
    """
    an item that refers to a collection of data from a data source.
    """

    # Class Variables
    _category: ClassVar[str] = "Dataset"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class DatasetDistribution(InformationContentEntity):
    """
    an item that holds distribution level information about a dataset.
    """

    # Class Variables
    _category: ClassVar[str] = "DatasetDistribution"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    distribution_download_url: Optional[str] = None


@dataclass(config=PydanticConfig)
class DatasetVersion(InformationContentEntity):
    """
    an item that holds version level information about a dataset.
    """

    # Class Variables
    _category: ClassVar[str] = "DatasetVersion"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    has_dataset: Optional[Union[Curie, Dataset]] = None
    ingest_date: Optional[str] = None
    has_distribution: Optional[Union[Curie, DatasetDistribution]] = None

    # Validators

    @validator('has_dataset')
    def check_has_dataset_prefix(cls, field):
        check_curie_prefix(Dataset, field)
        return field

    @validator('has_distribution')
    def check_has_distribution_prefix(cls, field):
        check_curie_prefix(DatasetDistribution, field)
        return field


@dataclass(config=PydanticConfig)
class DatasetSummary(InformationContentEntity):
    """
    an item that holds summary level information about a dataset.
    """

    # Class Variables
    _category: ClassVar[str] = "DatasetSummary"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    source_web_page: Optional[str] = None
    source_logo: Optional[str] = None


@dataclass(config=PydanticConfig)
class ConfidenceLevel(InformationContentEntity):
    """
    Level of confidence in a statement
    """

    # Class Variables
    _category: ClassVar[str] = "ConfidenceLevel"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class EvidenceType(InformationContentEntity):
    """
    Class of evidence that supports an association
    """

    # Class Variables
    _category: ClassVar[str] = "EvidenceType"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Publication(InformationContentEntity):
    """
    Any published piece of information. Can refer to a whole publication, its encompassing publication (i.e. journal
    or book) or to a part of a publication, if of significant knowledge scope (e.g. a figure, figure legend, or
    section highlighted by NLP). The scope is intended to be general and include information published on the web, as
    well as printed materials, either directly or in one of the Publication Biolink category subclasses.
    """

    # Class Variables
    _category: ClassVar[str] = "Publication"
    _required_attributes: ClassVar[List[str]] = ["category", "id", "type"]
    _id_prefixes: ClassVar[List[str]] = ["NLMID"]

    id: Curie = None
    type: str = None
    authors: Optional[Union[str, List[str]]] = field(default_factory=list)
    pages: Optional[Union[str, List[str]]] = field(default_factory=list)
    summary: Optional[str] = None
    keywords: Optional[Union[str, List[str]]] = field(default_factory=list)
    mesh_terms: Optional[Union[Curie, List[Curie]]] = field(default_factory=list)
    xref: Optional[Union[IriType, List[IriType]]] = field(default_factory=list)
    name: Optional[Union[str, LabelType]] = None

    # Validators

    @validator('authors')
    def convert_authors_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)

    @validator('pages')
    def convert_pages_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)

    @validator('keywords')
    def convert_keywords_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)

    @validator('mesh_terms')
    def convert_mesh_terms_to_list_check_curies(cls, field):
        return convert_scalar_to_list_check_curies(cls, field)

    @validator('xref')
    def convert_xref_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)

    @validator('id')
    def check_id_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class Book(Publication):
    """
    This class may rarely be instantiated except if use cases of a given knowledge graph support its utility.
    """

    # Class Variables
    _category: ClassVar[str] = "Book"
    _required_attributes: ClassVar[List[str]] = ["category", "id", "type"]
    _id_prefixes: ClassVar[List[str]] = ["isbn", "NLMID"]

    id: Curie = None
    type: str = None

    # Validators

    @validator('id')
    def check_id_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class BookChapter(Publication):

    # Class Variables
    _category: ClassVar[str] = "BookChapter"
    _required_attributes: ClassVar[List[str]] = ["category", "id", "type", "published_in"]

    published_in: Curie = None
    volume: Optional[str] = None
    chapter: Optional[str] = None

    # Validators

    @validator('published_in')
    def check_published_in_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class Serial(Publication):
    """
    This class may rarely be instantiated except if use cases of a given knowledge graph support its utility.
    """

    # Class Variables
    _category: ClassVar[str] = "Serial"
    _required_attributes: ClassVar[List[str]] = ["category", "id", "type"]
    _id_prefixes: ClassVar[List[str]] = ["issn", "NLMID"]

    id: Curie = None
    type: str = None
    iso_abbreviation: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None

    # Validators

    @validator('id')
    def check_id_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class Article(Publication):

    # Class Variables
    _category: ClassVar[str] = "Article"
    _required_attributes: ClassVar[List[str]] = ["category", "id", "type", "published_in"]
    _id_prefixes: ClassVar[List[str]] = ["PMID"]

    published_in: Curie = None
    iso_abbreviation: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None

    # Validators

    @validator('published_in')
    def check_published_in_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class PhysicalEssenceOrOccurrent:
    """
    Either a physical or processual entity.
    """


@dataclass(config=PydanticConfig)
class PhysicalEssence(PhysicalEssenceOrOccurrent):
    """
    Semantic mixin concept.  Pertains to entities that have physical properties such as mass, volume, or charge.
    """


@dataclass(config=PydanticConfig)
class PhysicalEntity(NamedThing, PhysicalEssence):
    """
    An entity that has material reality (a.k.a. physical essence).
    """

    # Class Variables
    _category: ClassVar[str] = "PhysicalEntity"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Occurrent(PhysicalEssenceOrOccurrent):
    """
    A processual entity.
    """


@dataclass(config=PydanticConfig)
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

    # Class Variables
    _category: ClassVar[str] = "Activity"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Procedure(NamedThing, ActivityAndBehavior):
    """
    A series of actions conducted in a certain order or manner
    """

    # Class Variables
    _category: ClassVar[str] = "Procedure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Phenomenon(NamedThing, Occurrent):
    """
    a fact or situation that is observed to exist or happen, especially one whose cause or explanation is in question
    """

    # Class Variables
    _category: ClassVar[str] = "Phenomenon"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Device(NamedThing):
    """
    A thing made or adapted for a particular purpose, especially a piece of mechanical or electronic equipment
    """

    # Class Variables
    _category: ClassVar[str] = "Device"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
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

    # Class Variables
    _category: ClassVar[str] = "MaterialSample"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["BIOSAMPLE", "GOLD.META"]


@dataclass(config=PydanticConfig)
class PlanetaryEntity(NamedThing):
    """
    Any entity or process that exists at the level of the whole planet
    """

    # Class Variables
    _category: ClassVar[str] = "PlanetaryEntity"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class EnvironmentalProcess(PlanetaryEntity, Occurrent):

    # Class Variables
    _category: ClassVar[str] = "EnvironmentalProcess"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class EnvironmentalFeature(PlanetaryEntity):

    # Class Variables
    _category: ClassVar[str] = "EnvironmentalFeature"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class GeographicLocation(PlanetaryEntity):
    """
    a location that can be described in lat/long coordinates
    """

    # Class Variables
    _category: ClassVar[str] = "GeographicLocation"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass(config=PydanticConfig)
class GeographicLocationAtTime(GeographicLocation):
    """
    a location that can be described in lat/long coordinates, for a particular time
    """

    # Class Variables
    _category: ClassVar[str] = "GeographicLocationAtTime"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    timepoint: Optional[Union[str, TimeType]] = None


@dataclass(config=PydanticConfig)
class BiologicalEntity(NamedThing):

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class ThingWithTaxon:
    """
    A mixin that can be used on any entity that can be taxonomically classified. This includes individual organisms;
    genes, their products and other molecular entities; body parts; biological processes
    """

    in_taxon: Optional[
        Union[Union[Curie, OrganismTaxon], List[Union[Curie, OrganismTaxon]]]
    ] = field(default_factory=list)

    # Validators

    @validator('in_taxon')
    def convert_in_taxon_to_list_check_curies(cls, field):
        return convert_scalar_to_list_check_curies(OrganismTaxon, field)


@dataclass(config=PydanticConfig)
class MolecularEntity(BiologicalEntity, ThingWithTaxon, PhysicalEssence, OntologyClass):
    """
    A gene, gene product, small molecule or macromolecule (including protein complex)"
    """

    # Class Variables
    _category: ClassVar[str] = "MolecularEntity"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class BiologicalProcessOrActivity(BiologicalEntity, Occurrent, OntologyClass):
    """
    Either an individual molecular activity, or a collection of causally connected molecular activities in a
    biological system.
    """

    # Class Variables
    _category: ClassVar[str] = "BiologicalProcessOrActivity"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["GO", "REACT"]

    has_input: Optional[Union[Curie, List[Curie]]] = field(default_factory=list)
    has_output: Optional[Union[Curie, List[Curie]]] = field(default_factory=list)
    enabled_by: Optional[Union[Curie, List[Curie]]] = field(default_factory=list)

    # Validators

    @validator('has_input')
    def convert_has_input_to_list_check_curies(cls, field):
        return convert_scalar_to_list_check_curies(cls, field)

    @validator('has_output')
    def convert_has_output_to_list_check_curies(cls, field):
        return convert_scalar_to_list_check_curies(cls, field)

    @validator('enabled_by')
    def convert_enabled_by_to_list_check_curies(cls, field):
        return convert_scalar_to_list_check_curies(cls, field)


@dataclass(config=PydanticConfig)
class MolecularActivity(BiologicalProcessOrActivity, Occurrent, OntologyClass):
    """
    An execution of a molecular function carried out by a gene product or macromolecular complex.
    """

    # Class Variables
    _category: ClassVar[str] = "MolecularActivity"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = [
        "GO",
        "REACT",
        "RHEA",
        "MetaCyc",
        "EC",
        "TCDB",
        "KEGG.REACTION",
        "KEGG.RCLASS",
        "KEGG.ENZYME",
    ]

    has_input: Optional[Union[Curie, List[Curie]]] = field(default_factory=list)
    has_output: Optional[Union[Curie, List[Curie]]] = field(default_factory=list)
    enabled_by: Optional[Union[Curie, List[Curie]]] = field(default_factory=list)

    # Validators

    @validator('has_input')
    def convert_has_input_to_list_check_curies(cls, field):
        return convert_scalar_to_list_check_curies(cls, field)

    @validator('has_output')
    def convert_has_output_to_list_check_curies(cls, field):
        return convert_scalar_to_list_check_curies(cls, field)

    @validator('enabled_by')
    def convert_enabled_by_to_list_check_curies(cls, field):
        return convert_scalar_to_list_check_curies(cls, field)


@dataclass(config=PydanticConfig)
class BiologicalProcess(BiologicalProcessOrActivity, Occurrent, OntologyClass):
    """
    One or more causally connected executions of molecular functions
    """

    # Class Variables
    _category: ClassVar[str] = "BiologicalProcess"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["GO", "REACT", "MetaCyc", "KEGG.MODULE"]


@dataclass(config=PydanticConfig)
class Pathway(BiologicalProcess, OntologyClass):

    # Class Variables
    _category: ClassVar[str] = "Pathway"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = [
        "GO",
        "REACT",
        "KEGG",
        "SMPDB",
        "MSigDB",
        "PHARMGKB.PATHWAYS",
        "WIKIPATHWAYS",
        "FB",
        "PANTHER.PATHWAY",
    ]


@dataclass(config=PydanticConfig)
class PhysiologicalProcess(BiologicalProcess, OntologyClass):

    # Class Variables
    _category: ClassVar[str] = "PhysiologicalProcess"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["GO", "REACT"]


@dataclass(config=PydanticConfig)
class Behavior(BiologicalProcess, OntologyClass):

    # Class Variables
    _category: ClassVar[str] = "Behavior"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Death(BiologicalProcess):

    # Class Variables
    _category: ClassVar[str] = "Death"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Mixture:
    """
    The physical combination of two or more molecular entities in which the identities are retained and are mixed in
    the form of solutions, suspensions and colloids.
    """

    has_constituent: Optional[Union[Curie, List[Curie]]] = field(default_factory=list)

    # Validators

    @validator('has_constituent')
    def convert_has_constituent_to_list_check_curies(cls, field):
        return convert_scalar_to_list_check_curies(cls, field)


@dataclass(config=PydanticConfig)
class ChemicalSubstance(MolecularEntity, OntologyClass):
    """
    May be a chemical entity or a formulation with a chemical entity as active ingredient, or a complex material with
    multiple chemical entities as part
    """

    # Class Variables
    _category: ClassVar[str] = "ChemicalSubstance"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = [
        "PUBCHEM.COMPOUND",
        "CHEMBL.COMPOUND",
        "UNII",
        "CHEBI",
        "DRUGBANK",
        "MESH",
        "CAS",
        "DrugCentral",
        "GTOPDB",
        "HMDB",
        "KEGG.COMPOUND",
        "ChemBank",
        "Aeolus",
        "PUBCHEM.SUBSTANCE",
        "SIDER.DRUG",
        "INCHI",
        "INCHIKEY",
        "KEGG.GLYCAN",
        "KEGG.DRUG",
        "KEGG.DGROUP",
        "KEGG.ENVIRON",
    ]

    is_metabolite: Optional[bool] = None


@dataclass(config=PydanticConfig)
class Carbohydrate(ChemicalSubstance):

    # Class Variables
    _category: ClassVar[str] = "Carbohydrate"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["PUBCHEM.SUBSTANCE"]


@dataclass(config=PydanticConfig)
class ProcessedMaterial(ChemicalSubstance, Mixture, OntologyClass):
    """
    A chemical substance (often a mixture) processed for consumption for nutritional, medical or technical use.
    """

    # Class Variables
    _category: ClassVar[str] = "ProcessedMaterial"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Drug(MolecularEntity, Mixture, ChemicalOrDrugOrTreatment, OntologyClass):
    """
    A substance intended for use in the diagnosis, cure, mitigation, treatment, or prevention of disease
    """

    # Class Variables
    _category: ClassVar[str] = "Drug"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["RXCUI", "NDC", "PHARMGKB.DRUG"]


@dataclass(config=PydanticConfig)
class FoodComponent(ChemicalSubstance):

    # Class Variables
    _category: ClassVar[str] = "FoodComponent"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class EnvironmentalFoodContaminant(ChemicalSubstance):

    # Class Variables
    _category: ClassVar[str] = "EnvironmentalFoodContaminant"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class FoodAdditive(ChemicalSubstance):

    # Class Variables
    _category: ClassVar[str] = "FoodAdditive"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Nutrient(ChemicalSubstance):

    # Class Variables
    _category: ClassVar[str] = "Nutrient"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Macronutrient(Nutrient):

    # Class Variables
    _category: ClassVar[str] = "Macronutrient"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Micronutrient(Nutrient):

    # Class Variables
    _category: ClassVar[str] = "Micronutrient"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Vitamin(Micronutrient):

    # Class Variables
    _category: ClassVar[str] = "Vitamin"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Food(MolecularEntity, Mixture):
    """
    A substance consumed by a living organism as a source of nutrition
    """

    # Class Variables
    _category: ClassVar[str] = "Food"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["foodb.compound"]


@dataclass(config=PydanticConfig)
class Metabolite(ChemicalSubstance):
    """
    Any intermediate or product resulting from metabolism. Includes primary and secondary metabolites.
    """

    # Class Variables
    _category: ClassVar[str] = "Metabolite"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class OrganismAttribute(Attribute):
    """
    describes a characteristic of an organismal entity.
    """

    # Class Variables
    _category: ClassVar[str] = "OrganismAttribute"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]


@dataclass(config=PydanticConfig)
class PhenotypicQuality(OrganismAttribute):
    """
    A property of a phenotype
    """

    # Class Variables
    _category: ClassVar[str] = "PhenotypicQuality"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]


@dataclass(config=PydanticConfig)
class Inheritance(OrganismAttribute):
    """
    The pattern or 'mode' in which a particular genetic trait or disorder is passed from one generation to the next,
    e.g. autosomal dominant, autosomal recessive, etc.
    """

    # Class Variables
    _category: ClassVar[str] = "Inheritance"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]


@dataclass(config=PydanticConfig)
class OrganismalEntity(BiologicalEntity):
    """
    A named entity that is either a part of an organism, a whole organism, population or clade of organisms, excluding
    molecular entities
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    has_attribute: Optional[Union[Union[str, Attribute], List[Union[str, Attribute]]]] = field(
        default_factory=list
    )

    # Validators

    @validator('has_attribute')
    def convert_has_attribute_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)


@dataclass(config=PydanticConfig)
class LifeStage(OrganismalEntity, ThingWithTaxon):
    """
    A stage of development or growth of an organism, including post-natal adult stages
    """

    # Class Variables
    _category: ClassVar[str] = "LifeStage"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class IndividualOrganism(OrganismalEntity, ThingWithTaxon):
    """
    An instance of an organism. For example, Richard Nixon, Charles Darwin, my pet cat. Example ID:
    ORCID:0000-0002-5355-2576
    """

    # Class Variables
    _category: ClassVar[str] = "IndividualOrganism"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["ORCID"]


@dataclass(config=PydanticConfig)
class PopulationOfIndividualOrganisms(OrganismalEntity, ThingWithTaxon):
    """
    A collection of individuals from the same taxonomic class distinguished by one or more characteristics.
    Characteristics can include, but are not limited to, shared geographic location, genetics, phenotypes [Alliance
    for Genome Resources]
    """

    # Class Variables
    _category: ClassVar[str] = "PopulationOfIndividualOrganisms"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["HANCESTRO"]


@dataclass(config=PydanticConfig)
class StudyPopulation(PopulationOfIndividualOrganisms):
    """
    A group of people banded together or treated as a group as participants in a research study.
    """

    # Class Variables
    _category: ClassVar[str] = "StudyPopulation"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class DiseaseOrPhenotypicFeature(BiologicalEntity, ThingWithTaxon):
    """
    Either one of a disease or an individual phenotypic feature. Some knowledge resources such as Monarch treat these
    as distinct, others such as MESH conflate.
    """

    # Class Variables
    _category: ClassVar[str] = "DiseaseOrPhenotypicFeature"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Disease(DiseaseOrPhenotypicFeature):

    # Class Variables
    _category: ClassVar[str] = "Disease"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = [
        "MONDO",
        "DOID",
        "OMIM",
        "ORPHANET",
        "EFO",
        "UMLS",
        "MESH",
        "MEDDRA",
        "NCIT",
        "SNOMEDCT",
        "medgen",
        "ICD10",
        "ICD9",
        "ICD0",
        "KEGG.DISEASE",
        "HP",
        "MP",
    ]


@dataclass(config=PydanticConfig)
class PhenotypicFeature(DiseaseOrPhenotypicFeature):

    # Class Variables
    _category: ClassVar[str] = "PhenotypicFeature"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = [
        "HP",
        "EFO",
        "NCIT",
        "UMLS",
        "MEDDRA",
        "MP",
        "ZP",
        "UPHENO",
        "APO",
        "FBcv",
        "WBPhenotype",
        "SNOMEDCT",
        "MESH",
    ]


@dataclass(config=PydanticConfig)
class BehavioralFeature(PhenotypicFeature):
    """
    A phenotypic feature which is behavioral in nature.
    """

    # Class Variables
    _category: ClassVar[str] = "BehavioralFeature"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class AnatomicalEntity(OrganismalEntity, ThingWithTaxon, PhysicalEssence):
    """
    A subcellular location, cell type or gross anatomical part
    """

    # Class Variables
    _category: ClassVar[str] = "AnatomicalEntity"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["UBERON", "GO", "CL", "UMLS", "MESH", "NCIT"]


@dataclass(config=PydanticConfig)
class CellularComponent(AnatomicalEntity):
    """
    A location in or around a cell
    """

    # Class Variables
    _category: ClassVar[str] = "CellularComponent"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["GO", "MESH", "UMLS", "NCIT", "SNOMEDCT", "CL", "UBERON"]


@dataclass(config=PydanticConfig)
class Cell(AnatomicalEntity):

    # Class Variables
    _category: ClassVar[str] = "Cell"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["CL", "PO", "UMLS", "NCIT", "MESH", "UBERON", "SNOMEDCT"]


@dataclass(config=PydanticConfig)
class CellLine(OrganismalEntity):

    # Class Variables
    _category: ClassVar[str] = "CellLine"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["CLO"]


@dataclass(config=PydanticConfig)
class GrossAnatomicalStructure(AnatomicalEntity):

    # Class Variables
    _category: ClassVar[str] = "GrossAnatomicalStructure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["UBERON", "UMLS", "MESH", "NCIT", "PO", "FAO"]


@dataclass(config=PydanticConfig)
class MacromolecularMachineMixin:
    """
    A union of gene locus, gene product, and macromolecular complex mixin. These are the basic units of function in a
    cell. They either carry out individual biological activities, or they encode molecules which do this.
    """

    name: Optional[Union[str, SymbolType]] = None


@dataclass(config=PydanticConfig)
class GeneOrGeneProduct(MacromolecularMachineMixin):
    """
    A union of gene loci or gene products. Frequently an identifier for one will be used as proxy for another
    """

    # Class Variables
    _id_prefixes: ClassVar[List[str]] = ["CHEMBL.TARGET", "IUPHAR.FAMILY"]


@dataclass(config=PydanticConfig)
class GeneProductMixin(GeneOrGeneProduct):
    """
    The functional molecular product of a single gene locus. Gene products are either proteins or functional RNA
    molecules.
    """

    # Class Variables
    _id_prefixes: ClassVar[List[str]] = ["UniProtKB", "gtpo", "PR"]

    synonym: Optional[Union[Union[str, LabelType], List[Union[str, LabelType]]]] = field(
        default_factory=list
    )
    xref: Optional[Union[IriType, List[IriType]]] = field(default_factory=list)

    # Validators

    @validator('synonym')
    def convert_synonym_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)

    @validator('xref')
    def convert_xref_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)


@dataclass(config=PydanticConfig)
class GeneProductIsoformMixin(GeneProductMixin):
    """
    This is an abstract class that can be mixed in with different kinds of gene products to indicate that the gene
    product is intended to represent a specific isoform rather than a canonical or reference or generic product. The
    designation of canonical or reference may be arbitrary, or it may represent the superclass of all isoforms.
    """


@dataclass(config=PydanticConfig)
class MacromolecularComplexMixin(MacromolecularMachineMixin):
    """
    A stable assembly of two or more macromolecules, i.e. proteins, nucleic acids, carbohydrates or lipids, in which
    at least one component is a protein and the constituent parts function together.
    """

    # Class Variables
    _id_prefixes: ClassVar[List[str]] = ["INTACT", "GO", "PR", "REACT"]


@dataclass(config=PydanticConfig)
class GenomicEntity(MolecularEntity):
    """
    an entity that can either be directly located on a genome (gene, transcript, exon, regulatory region) or is
    encoded in a genome (protein)
    """

    # Class Variables
    _category: ClassVar[str] = "GenomicEntity"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    has_biological_sequence: Optional[Union[str, BiologicalSequence]] = None


@dataclass(config=PydanticConfig)
class Gene(GenomicEntity, GeneOrGeneProduct):
    """
    A region (or regions) that includes all of the sequence elements necessary to encode a functional transcript. A
    gene locus may include regulatory regions, transcribed regions and/or other functional sequence regions.
    """

    # Class Variables
    _category: ClassVar[str] = "Gene"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = [
        "NCBIGene",
        "ENSEMBL",
        "HGNC",
        "MGI",
        "ZFIN",
        "dictyBase",
        "WB",
        "WormBase",
        "FB",
        "FB",
        "RGD",
        "SGD",
        "POMBASE",
        "OMIM",
        "KEGG.GENE",
        "UMLS",
    ]

    symbol: Optional[str] = None
    synonym: Optional[Union[Union[str, LabelType], List[Union[str, LabelType]]]] = field(
        default_factory=list
    )
    xref: Optional[Union[IriType, List[IriType]]] = field(default_factory=list)

    # Validators

    @validator('synonym')
    def convert_synonym_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)

    @validator('xref')
    def convert_xref_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)


@dataclass(config=PydanticConfig)
class Genome(GenomicEntity):
    """
    A genome is the sum of genetic material within a cell or virion.
    """

    # Class Variables
    _category: ClassVar[str] = "Genome"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Exon(GenomicEntity):
    """
    A region of the transcript sequence within a gene which is not removed from the primary RNA transcript by RNA
    splicing.
    """

    # Class Variables
    _category: ClassVar[str] = "Exon"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Transcript(GenomicEntity):
    """
    An RNA synthesized on a DNA or RNA template by an RNA polymerase.
    """

    # Class Variables
    _category: ClassVar[str] = "Transcript"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["ENSEMBL", "FB"]


@dataclass(config=PydanticConfig)
class CodingSequence(GenomicEntity):

    # Class Variables
    _category: ClassVar[str] = "CodingSequence"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Protein(GenomicEntity, GeneProductMixin):
    """
    A gene product that is composed of a chain of amino acid sequences and is produced by ribosome-mediated
    translation of mRNA
    """

    # Class Variables
    _category: ClassVar[str] = "Protein"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["UniProtKB", "PR", "ENSEMBL", "FB", "UMLS"]


@dataclass(config=PydanticConfig)
class ProteinIsoform(Protein, GeneProductIsoformMixin):
    """
    Represents a protein that is a specific isoform of the canonical or reference protein. See
    https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4114032/
    """

    # Class Variables
    _category: ClassVar[str] = "ProteinIsoform"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["UniProtKB", "UNIPROT.ISOFORM", "PR", "ENSEMBL"]


@dataclass(config=PydanticConfig)
class RNAProduct(Transcript, GeneProductMixin):

    # Class Variables
    _category: ClassVar[str] = "RNAProduct"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["RNACENTRAL"]


@dataclass(config=PydanticConfig)
class RNAProductIsoform(RNAProduct, GeneProductIsoformMixin):
    """
    Represents a protein that is a specific isoform of the canonical or reference RNA
    """

    # Class Variables
    _category: ClassVar[str] = "RNAProductIsoform"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["RNACENTRAL"]


@dataclass(config=PydanticConfig)
class NoncodingRNAProduct(RNAProduct):

    # Class Variables
    _category: ClassVar[str] = "NoncodingRNAProduct"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["RNACENTRAL", "NCBIGene", "ENSEMBL"]


@dataclass(config=PydanticConfig)
class MicroRNA(NoncodingRNAProduct):

    # Class Variables
    _category: ClassVar[str] = "MicroRNA"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["MIR", "HGNC", "WormBase"]


@dataclass(config=PydanticConfig)
class SiRNA(NoncodingRNAProduct):
    """
    A small RNA molecule that is the product of a longer exogenous or endogenous dsRNA, which is either a bimolecular
    duplex or very long hairpin, processed (via the Dicer pathway) such that numerous siRNAs accumulate from both
    strands of the dsRNA. SRNAs trigger the cleavage of their target molecules.
    """

    # Class Variables
    _category: ClassVar[str] = "SiRNA"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["MIR", "HGNC", "WormBase"]


@dataclass(config=PydanticConfig)
class GeneGroupingMixin:
    """
    any grouping of multiple genes or gene products
    """

    has_gene_or_gene_product: Optional[Union[Union[Curie, Gene], List[Union[Curie, Gene]]]] = field(
        default_factory=list
    )

    # Validators

    @validator('has_gene_or_gene_product')
    def convert_has_gene_or_gene_product_to_list_check_curies(cls, field):
        return convert_scalar_to_list_check_curies(Gene, field)


@dataclass(config=PydanticConfig)
class GeneFamily(MolecularEntity, GeneGroupingMixin):
    """
    any grouping of multiple genes or gene products related by common descent
    """

    # Class Variables
    _category: ClassVar[str] = "GeneFamily"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = [
        "PANTHER.FAMILY",
        "HGNC.FAMILY",
        "FB",
        "interpro",
        "CATH",
        "CDD",
        "HAMAP",
        "PFAM",
        "PIRSF",
        "PRINTS",
        "PRODOM",
        "PROSITE",
        "SMART",
        "SUPFAM",
        "TIGRFAM",
        "CATH.SUPERFAMILY",
        "RFAM",
        "KEGG.ORTHOLOGY",
        "EGGNOG",
    ]


@dataclass(config=PydanticConfig)
class Zygosity(Attribute):

    # Class Variables
    _category: ClassVar[str] = "Zygosity"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]


@dataclass(config=PydanticConfig)
class Genotype(GenomicEntity):
    """
    An information content entity that describes a genome by specifying the total variation in genomic sequence and/or
    gene expression, relative to some established background
    """

    # Class Variables
    _category: ClassVar[str] = "Genotype"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["ZFIN", "FB"]

    has_zygosity: Optional[Union[str, Zygosity]] = None


@dataclass(config=PydanticConfig)
class Haplotype(GenomicEntity):
    """
    A set of zero or more Alleles on a single instance of a Sequence[VMC]
    """

    # Class Variables
    _category: ClassVar[str] = "Haplotype"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class SequenceVariant(GenomicEntity):
    """
    An allele that varies in its sequence from what is considered the reference allele at that locus.
    """

    # Class Variables
    _category: ClassVar[str] = "SequenceVariant"
    _required_attributes: ClassVar[List[str]] = ["category", "id"]
    _id_prefixes: ClassVar[List[str]] = [
        "CAID",
        "CLINVAR",
        "ClinVarVariant",
        "WIKIDATA",
        "DBSNP",
        "DBSNP",
        "MGI",
        "ZFIN",
        "FB",
        "WB",
        "WormBase",
    ]

    id: Curie = None
    has_gene: Optional[Union[Union[Curie, Gene], List[Union[Curie, Gene]]]] = field(
        default_factory=list
    )
    has_biological_sequence: Optional[Union[str, BiologicalSequence]] = None

    # Validators

    @validator('has_gene')
    def convert_has_gene_to_list_check_curies(cls, field):
        return convert_scalar_to_list_check_curies(Gene, field)

    @validator('id')
    def check_id_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class Snv(SequenceVariant):
    """
    SNVs are single nucleotide positions in genomic DNA at which different sequence alternatives exist
    """

    # Class Variables
    _category: ClassVar[str] = "Snv"
    _required_attributes: ClassVar[List[str]] = ["category", "id"]


@dataclass(config=PydanticConfig)
class ReagentTargetedGene(GenomicEntity):
    """
    A gene altered in its expression level in the context of some experiment as a result of being targeted by
    gene-knockdown reagent(s) such as a morpholino or RNAi.
    """

    # Class Variables
    _category: ClassVar[str] = "ReagentTargetedGene"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class ClinicalAttribute(Attribute):
    """
    Attributes relating to a clinical manifestation
    """

    # Class Variables
    _category: ClassVar[str] = "ClinicalAttribute"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]


@dataclass(config=PydanticConfig)
class ClinicalMeasurement(ClinicalAttribute):
    """
    A clinical measurement is a special kind of attribute which results from a laboratory observation from a subject
    individual or sample. Measurements can be connected to their subject by the 'has attribute' slot.
    """

    # Class Variables
    _category: ClassVar[str] = "ClinicalMeasurement"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]

    has_attribute_type: Union[str, OntologyClass] = None


@dataclass(config=PydanticConfig)
class ClinicalModifier(ClinicalAttribute):
    """
    Used to characterize and specify the phenotypic abnormalities defined in the phenotypic abnormality sub-ontology,
    with respect to severity, laterality, and other aspects
    """

    # Class Variables
    _category: ClassVar[str] = "ClinicalModifier"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]


@dataclass(config=PydanticConfig)
class ClinicalCourse(ClinicalAttribute):
    """
    The course a disease typically takes from its onset, progression in time, and eventual resolution or death of the
    affected individual
    """

    # Class Variables
    _category: ClassVar[str] = "ClinicalCourse"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]


@dataclass(config=PydanticConfig)
class Onset(ClinicalCourse):
    """
    The age group in which (disease) symptom manifestations appear
    """

    # Class Variables
    _category: ClassVar[str] = "Onset"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]


@dataclass(config=PydanticConfig)
class ClinicalEntity(NamedThing):
    """
    Any entity or process that exists in the clinical domain and outside the biological realm. Diseases are placed
    under biological entities
    """

    # Class Variables
    _category: ClassVar[str] = "ClinicalEntity"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class ClinicalTrial(ClinicalEntity):

    # Class Variables
    _category: ClassVar[str] = "ClinicalTrial"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class ClinicalIntervention(ClinicalEntity):

    # Class Variables
    _category: ClassVar[str] = "ClinicalIntervention"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class ClinicalFinding(PhenotypicFeature):
    """
    this category is currently considered broad enough to tag clinical lab measurements and other biological
    attributes taken as 'clinical traits' with some statistical score, for example, a p value in genetic associations.
    """

    # Class Variables
    _category: ClassVar[str] = "ClinicalFinding"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]
    _id_prefixes: ClassVar[List[str]] = ["LOINC", "NCIT", "EFO"]

    has_attribute: Optional[
        Union[Union[str, ClinicalAttribute], List[Union[str, ClinicalAttribute]]]
    ] = field(default_factory=list)

    # Validators

    @validator('has_attribute')
    def convert_has_attribute_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)


@dataclass(config=PydanticConfig)
class Hospitalization(ClinicalIntervention):

    # Class Variables
    _category: ClassVar[str] = "Hospitalization"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class SocioeconomicAttribute(Attribute):
    """
    Attributes relating to a socioeconomic manifestation
    """

    # Class Variables
    _category: ClassVar[str] = "SocioeconomicAttribute"
    _required_attributes: ClassVar[List[str]] = ["has_attribute_type"]


@dataclass(config=PydanticConfig)
class Case(IndividualOrganism):
    """
    An individual (human) organism that has a patient role in some clinical context.
    """

    # Class Variables
    _category: ClassVar[str] = "Case"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Cohort(StudyPopulation):
    """
    A group of people banded together or treated as a group who share common characteristics. A cohort 'study' is a
    particular form of longitudinal study that samples a cohort, performing a cross-section at intervals through time.
    """

    # Class Variables
    _category: ClassVar[str] = "Cohort"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


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

    # Class Variables
    _category: ClassVar[str] = "GenomicBackgroundExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
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

    # Class Variables
    _category: ClassVar[str] = "PathologicalProcess"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class PathologicalProcessExposure(PathologicalProcess, ExposureEvent):
    """
    A pathological process, when viewed as an exposure, representing an precondition, leading to or influencing an
    outcome, e.g. autoimmunity leading to disease.
    """

    # Class Variables
    _category: ClassVar[str] = "PathologicalProcessExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class PathologicalAnatomicalStructure(AnatomicalEntity, PathologicalEntityMixin):
    """
    An anatomical structure with the potential of have an abnormal or deleterious effect at the subcellular, cellular,
    multicellular, or organismal level.
    """

    # Class Variables
    _category: ClassVar[str] = "PathologicalAnatomicalStructure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class PathologicalAnatomicalExposure(PathologicalAnatomicalStructure, ExposureEvent):
    """
    An abnormal anatomical structure, when viewed as an exposure, representing an precondition, leading to or
    influencing an outcome, e.g. thrombosis leading to an ischemic disease outcome.
    """

    # Class Variables
    _category: ClassVar[str] = "PathologicalAnatomicalExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class DiseaseOrPhenotypicFeatureExposure(
    DiseaseOrPhenotypicFeature, ExposureEvent, PathologicalEntityMixin
):
    """
    A disease or phenotypic feature state, when viewed as an exposure, represents an precondition, leading to or
    influencing an outcome, e.g. HIV predisposing an individual to infections; a relative deficiency of skin
    pigmentation predisposing an individual to skin cancer.
    """

    # Class Variables
    _category: ClassVar[str] = "DiseaseOrPhenotypicFeatureExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class ChemicalExposure(ChemicalSubstance, ExposureEvent):
    """
    A chemical exposure is an intake of a particular chemical substance, other than a drug.
    """

    # Class Variables
    _category: ClassVar[str] = "ChemicalExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class ComplexChemicalExposure(ChemicalExposure, Mixture):
    """
    A complex chemical exposure is an intake of a chemical mixture (e.g. gasoline), other than a drug.
    """

    # Class Variables
    _category: ClassVar[str] = "ComplexChemicalExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class DrugExposure(Drug, ExposureEvent):
    """
    A drug exposure is an intake of a particular drug.
    """

    # Class Variables
    _category: ClassVar[str] = "DrugExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class DrugToGeneInteractionExposure(DrugExposure, GeneGroupingMixin):
    """
    drug to gene interaction exposure is a drug exposure is where the interactions of the drug with specific genes are
    known to constitute an 'exposure' to the organism, leading to or influencing an outcome.
    """

    # Class Variables
    _category: ClassVar[str] = "DrugToGeneInteractionExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Treatment(NamedThing, ExposureEvent, ChemicalOrDrugOrTreatment):
    """
    A treatment is targeted at a disease or phenotype and may involve multiple drug 'exposures', medical devices
    and/or procedures
    """

    # Class Variables
    _category: ClassVar[str] = "Treatment"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]

    has_drug: Optional[Union[Union[Curie, Drug], List[Union[Curie, Drug]]]] = field(
        default_factory=list
    )
    has_device: Optional[Union[Union[Curie, Device], List[Union[Curie, Device]]]] = field(
        default_factory=list
    )
    has_procedure: Optional[Union[Union[Curie, Procedure], List[Union[Curie, Procedure]]]] = field(
        default_factory=list
    )

    # Validators

    @validator('has_drug')
    def convert_has_drug_to_list_check_curies(cls, field):
        return convert_scalar_to_list_check_curies(Drug, field)

    @validator('has_device')
    def convert_has_device_to_list_check_curies(cls, field):
        return convert_scalar_to_list_check_curies(Device, field)

    @validator('has_procedure')
    def convert_has_procedure_to_list_check_curies(cls, field):
        return convert_scalar_to_list_check_curies(Procedure, field)


@dataclass(config=PydanticConfig)
class BioticExposure(OrganismTaxon, ExposureEvent):
    """
    An external biotic exposure is an intake of (sometimes pathological) biological organisms (including viruses).
    """

    # Class Variables
    _category: ClassVar[str] = "BioticExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class GeographicExposure(GeographicLocation, ExposureEvent):
    """
    A geographic exposure is a factor relating to geographic proximity to some impactful entity.
    """

    # Class Variables
    _category: ClassVar[str] = "GeographicExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class EnvironmentalExposure(EnvironmentalProcess, ExposureEvent):
    """
    A environmental exposure is a factor relating to abiotic processes in the environment including sunlight (UV-B),
    atmospheric (heat, cold, general pollution) and water-born contaminants.
    """

    # Class Variables
    _category: ClassVar[str] = "EnvironmentalExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class BehavioralExposure(Behavior, ExposureEvent):
    """
    A behavioral exposure is a factor relating to behavior impacting an individual.
    """

    # Class Variables
    _category: ClassVar[str] = "BehavioralExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class SocioeconomicExposure(Behavior, ExposureEvent):
    """
    A socioeconomic exposure is a factor relating to social and financial status of an affected individual (e.g.
    poverty).
    """

    # Class Variables
    _category: ClassVar[str] = "SocioeconomicExposure"
    _required_attributes: ClassVar[List[str]] = ["id", "category", "has_attribute"]

    has_attribute: Union[
        Union[str, SocioeconomicAttribute], List[Union[str, SocioeconomicAttribute]]
    ] = None

    # Validators

    @validator('has_attribute')
    def convert_has_attribute_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)


@dataclass(config=PydanticConfig)
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

    # Class Variables
    _category: ClassVar[str] = "PathologicalProcessOutcome"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class PathologicalAnatomicalOutcome(PathologicalAnatomicalStructure, Outcome):
    """
    An outcome resulting from an exposure event which is the manifestation of an abnormal anatomical structure.
    """

    # Class Variables
    _category: ClassVar[str] = "PathologicalAnatomicalOutcome"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class DiseaseOrPhenotypicFeatureOutcome(DiseaseOrPhenotypicFeature, Outcome):
    """
    Physiological outcomes resulting from an exposure event which is the manifestation of a disease or other
    characteristic phenotype.
    """

    # Class Variables
    _category: ClassVar[str] = "DiseaseOrPhenotypicFeatureOutcome"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class BehavioralOutcome(Behavior, Outcome):
    """
    An outcome resulting from an exposure event which is the manifestation of human behavior.
    """

    # Class Variables
    _category: ClassVar[str] = "BehavioralOutcome"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class HospitalizationOutcome(Hospitalization, Outcome):
    """
    An outcome resulting from an exposure event which is the increased manifestation of acute (e.g. emergency room
    visit) or chronic (inpatient) hospitalization.
    """

    # Class Variables
    _category: ClassVar[str] = "HospitalizationOutcome"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class MortalityOutcome(Death, Outcome):
    """
    An outcome of death from resulting from an exposure event.
    """

    # Class Variables
    _category: ClassVar[str] = "MortalityOutcome"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class EpidemiologicalOutcome(BiologicalEntity, Outcome):
    """
    An epidemiological outcome, such as societal disease burden, resulting from an exposure event.
    """

    # Class Variables
    _category: ClassVar[str] = "EpidemiologicalOutcome"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class SocioeconomicOutcome(Behavior, Outcome):
    """
    An general social or economic outcome, such as healthcare costs, utilization, etc., resulting from an exposure
    event
    """

    # Class Variables
    _category: ClassVar[str] = "SocioeconomicOutcome"
    _required_attributes: ClassVar[List[str]] = ["id", "category"]


@dataclass(config=PydanticConfig)
class Association(Entity):
    """
    A typed association between two entities, supported by evidence
    """

    # Class Variables
    _category: ClassVar[str] = "Association"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "object", "relation"]

    subject: Union[Curie, NamedThing] = None
    predicate: Curie = None
    object: Union[Curie, NamedThing] = None
    relation: Curie = None
    negated: Optional[bool] = None
    qualifiers: Optional[Union[Union[str, OntologyClass], List[Union[str, OntologyClass]]]] = field(
        default_factory=list
    )
    publications: Optional[
        Union[Union[Curie, Publication], List[Union[Curie, Publication]]]
    ] = field(default_factory=list)
    type: Optional[str] = None
    category: Optional[Union[Union[str, Curie], List[Union[str, Curie]]]] = field(
        default_factory=list
    )

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(NamedThing, field)
        return field

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(NamedThing, field)
        return field

    @validator('relation')
    def check_relation_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field

    @validator('qualifiers')
    def convert_qualifiers_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)

    @validator('publications')
    def convert_publications_to_list_check_curies(cls, field):
        return convert_scalar_to_list_check_curies(Publication, field)

    @validator('category')
    def convert_category_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)


@dataclass(config=PydanticConfig)
class ContributorAssociation(Association):
    """
    Any association between an entity (such as a publication) and various agents that contribute to its realisation
    """

    # Class Variables
    _category: ClassVar[str] = "ContributorAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "predicate", "object"]

    subject: Union[Curie, InformationContentEntity] = None
    predicate: Curie = None
    object: Union[Curie, Agent] = None
    qualifiers: Optional[Union[Union[str, OntologyClass], List[Union[str, OntologyClass]]]] = field(
        default_factory=list
    )

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(InformationContentEntity, field)
        return field

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(Agent, field)
        return field

    @validator('qualifiers')
    def convert_qualifiers_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)


@dataclass(config=PydanticConfig)
class GenotypeToGenotypePartAssociation(Association):
    """
    Any association between one genotype and a genotypic entity that is a sub-component of it
    """

    # Class Variables
    _category: ClassVar[str] = "GenotypeToGenotypePartAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "predicate", "subject", "object"]

    predicate: Curie = None
    subject: Union[Curie, Genotype] = None
    object: Union[Curie, Genotype] = None

    # Validators

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(Genotype, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(Genotype, field)
        return field


@dataclass(config=PydanticConfig)
class GenotypeToGeneAssociation(Association):
    """
    Any association between a genotype and a gene. The genotype have have multiple variants in that gene or a single
    one. There is no assumption of cardinality
    """

    # Class Variables
    _category: ClassVar[str] = "GenotypeToGeneAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "predicate", "subject", "object"]

    predicate: Curie = None
    subject: Union[Curie, Genotype] = None
    object: Union[Curie, Gene] = None

    # Validators

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(Genotype, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(Gene, field)
        return field


@dataclass(config=PydanticConfig)
class GenotypeToVariantAssociation(Association):
    """
    Any association between a genotype and a sequence variant.
    """

    # Class Variables
    _category: ClassVar[str] = "GenotypeToVariantAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "predicate", "subject", "object"]

    predicate: Curie = None
    subject: Union[Curie, Genotype] = None
    object: Union[Curie, SequenceVariant] = None

    # Validators

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(Genotype, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(SequenceVariant, field)
        return field


@dataclass(config=PydanticConfig)
class GeneToGeneAssociation(Association):
    """
    abstract parent class for different kinds of gene-gene or gene product to gene product relationships. Includes
    homology and interaction.
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    subject: Union[str, GeneOrGeneProduct] = None
    object: Union[str, GeneOrGeneProduct] = None


@dataclass(config=PydanticConfig)
class GeneToGeneHomologyAssociation(GeneToGeneAssociation):
    """
    A homology association between two genes. May be orthology (in which case the species of subject and object should
    differ) or paralogy (in which case the species may be the same)
    """

    # Class Variables
    _category: ClassVar[str] = "GeneToGeneHomologyAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    predicate: Curie = None

    # Validators

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class GeneExpressionMixin:
    """
    Observed gene expression intensity, context (site, stage) and associated phenotypic status within which the
    expression occurs.
    """

    quantifier_qualifier: Optional[Union[str, OntologyClass]] = None
    expression_site: Optional[Union[Curie, AnatomicalEntity]] = None
    stage_qualifier: Optional[Union[Curie, LifeStage]] = None
    phenotypic_state: Optional[Union[Curie, DiseaseOrPhenotypicFeature]] = None

    # Validators

    @validator('expression_site')
    def check_expression_site_prefix(cls, field):
        check_curie_prefix(AnatomicalEntity, field)
        return field

    @validator('stage_qualifier')
    def check_stage_qualifier_prefix(cls, field):
        check_curie_prefix(LifeStage, field)
        return field

    @validator('phenotypic_state')
    def check_phenotypic_state_prefix(cls, field):
        check_curie_prefix(DiseaseOrPhenotypicFeature, field)
        return field


@dataclass(config=PydanticConfig)
class GeneToGeneCoexpressionAssociation(GeneToGeneAssociation, GeneExpressionMixin):
    """
    Indicates that two genes are co-expressed, generally under the same conditions.
    """

    # Class Variables
    _category: ClassVar[str] = "GeneToGeneCoexpressionAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    predicate: Curie = None

    # Validators

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class PairwiseGeneToGeneInteraction(GeneToGeneAssociation):
    """
    An interaction between two genes or two gene products. May be physical (e.g. protein binding) or genetic (between
    genes). May be symmetric (e.g. protein interaction) or directed (e.g. phosphorylation)
    """

    # Class Variables
    _category: ClassVar[str] = "PairwiseGeneToGeneInteraction"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "object", "predicate", "relation"]

    predicate: Curie = None
    relation: Curie = None

    # Validators

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field

    @validator('relation')
    def check_relation_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class PairwiseMolecularInteraction(PairwiseGeneToGeneInteraction):
    """
    An interaction at the molecular level between two physical entities
    """

    # Class Variables
    _category: ClassVar[str] = "PairwiseMolecularInteraction"
    _required_attributes: ClassVar[List[str]] = ["subject", "id", "predicate", "relation", "object"]

    subject: Union[Curie, MolecularEntity] = None
    id: Curie = None
    predicate: Curie = None
    relation: Curie = None
    object: Union[Curie, MolecularEntity] = None
    interacting_molecules_category: Optional[Union[str, OntologyClass]] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(MolecularEntity, field)
        return field

    @validator('id')
    def check_id_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field

    @validator('relation')
    def check_relation_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(MolecularEntity, field)
        return field


@dataclass(config=PydanticConfig)
class CellLineToEntityAssociationMixin:
    """
    An relationship between a cell line and another entity
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[Curie, CellLine] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(CellLine, field)
        return field


@dataclass(config=PydanticConfig)
class MolecularEntityToEntityAssociationMixin:
    """
    An interaction between a molecular entity and another entity
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[Curie, MolecularEntity] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(MolecularEntity, field)
        return field


@dataclass(config=PydanticConfig)
class DrugToEntityAssociationMixin(MolecularEntityToEntityAssociationMixin):
    """
    An interaction between a drug and another entity
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[Curie, Drug] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(Drug, field)
        return field


@dataclass(config=PydanticConfig)
class ChemicalToEntityAssociationMixin(MolecularEntityToEntityAssociationMixin):
    """
    An interaction between a chemical entity and another entity
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[Curie, ChemicalSubstance] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(ChemicalSubstance, field)
        return field


@dataclass(config=PydanticConfig)
class CaseToEntityAssociationMixin:
    """
    An abstract association for use where the case is the subject
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[Curie, Case] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(Case, field)
        return field


@dataclass(config=PydanticConfig)
class ChemicalToChemicalAssociation(Association, ChemicalToEntityAssociationMixin):
    """
    A relationship between two chemical entities. This can encompass actual interactions as well as temporal causal
    edges, e.g. one chemical converted to another.
    """

    # Class Variables
    _category: ClassVar[str] = "ChemicalToChemicalAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "relation", "object"]

    object: Union[Curie, ChemicalSubstance] = None

    # Validators

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(ChemicalSubstance, field)
        return field


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

    # Class Variables
    _category: ClassVar[str] = "ChemicalToChemicalDerivationAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    subject: Union[Curie, ChemicalSubstance] = None
    object: Union[Curie, ChemicalSubstance] = None
    predicate: Curie = None
    catalyst_qualifier: Optional[
        Union[Union[str, MacromolecularMachineMixin], List[Union[str, MacromolecularMachineMixin]]]
    ] = field(default_factory=list)

    # Validators

    @validator('catalyst_qualifier')
    def convert_catalyst_qualifier_to_list_check_curies(cls, field):
        return convert_scalar_to_list(field)

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(ChemicalSubstance, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(ChemicalSubstance, field)
        return field

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class ChemicalToPathwayAssociation(Association, ChemicalToEntityAssociationMixin):
    """
    An interaction between a chemical entity and a biological process or pathway.
    """

    # Class Variables
    _category: ClassVar[str] = "ChemicalToPathwayAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "relation", "object"]

    object: Union[Curie, Pathway] = None

    # Validators

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(Pathway, field)
        return field


@dataclass(config=PydanticConfig)
class ChemicalToGeneAssociation(Association, ChemicalToEntityAssociationMixin):
    """
    An interaction between a chemical entity and a gene or gene product.
    """

    # Class Variables
    _category: ClassVar[str] = "ChemicalToGeneAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "relation", "object"]

    object: Union[str, GeneOrGeneProduct] = None


@dataclass(config=PydanticConfig)
class DrugToGeneAssociation(Association, DrugToEntityAssociationMixin):
    """
    An interaction between a drug and a gene or gene product.
    """

    # Class Variables
    _category: ClassVar[str] = "DrugToGeneAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "relation", "object"]

    object: Union[str, GeneOrGeneProduct] = None


@dataclass(config=PydanticConfig)
class MaterialSampleToEntityAssociationMixin:
    """
    An association between a material sample and something.
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[Curie, MaterialSample] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(MaterialSample, field)
        return field


@dataclass(config=PydanticConfig)
class MaterialSampleDerivationAssociation(Association):
    """
    An association between a material sample and the material entity from which it is derived.
    """

    # Class Variables
    _category: ClassVar[str] = "MaterialSampleDerivationAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    subject: Union[Curie, MaterialSample] = None
    object: Union[Curie, NamedThing] = None
    predicate: Curie = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(MaterialSample, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(NamedThing, field)
        return field

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class DiseaseToEntityAssociationMixin:

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[Curie, Disease] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(Disease, field)
        return field


@dataclass(config=PydanticConfig)
class EntityToExposureEventAssociationMixin:
    """
    An association between some entity and an exposure event.
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["object"]

    object: Union[str, ExposureEvent] = None


@dataclass(config=PydanticConfig)
class DiseaseToExposureEventAssociation(
    Association, DiseaseToEntityAssociationMixin, EntityToExposureEventAssociationMixin
):
    """
    An association between an exposure event and a disease.
    """

    # Class Variables
    _category: ClassVar[str] = "DiseaseToExposureEventAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "object", "relation"]


@dataclass(config=PydanticConfig)
class ExposureEventToEntityAssociationMixin:
    """
    An association between some exposure event and some entity.
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[str, ExposureEvent] = None


@dataclass(config=PydanticConfig)
class EntityToOutcomeAssociationMixin:
    """
    An association between some entity and an outcome
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["object"]

    object: Union[str, Outcome] = None


@dataclass(config=PydanticConfig)
class ExposureEventToOutcomeAssociation(
    Association, ExposureEventToEntityAssociationMixin, EntityToOutcomeAssociationMixin
):
    """
    An association between an exposure event and an outcome.
    """

    # Class Variables
    _category: ClassVar[str] = "ExposureEventToOutcomeAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "object", "relation"]

    has_population_context: Optional[Union[Curie, PopulationOfIndividualOrganisms]] = None
    has_temporal_context: Optional[Union[str, TimeType]] = None

    # Validators

    @validator('has_population_context')
    def check_has_population_context_prefix(cls, field):
        check_curie_prefix(PopulationOfIndividualOrganisms, field)
        return field


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

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["object"]

    object: Union[Curie, PhenotypicFeature] = None
    sex_qualifier: Optional[Union[str, BiologicalSex]] = None
    description: Optional[Union[str, NarrativeText]] = None

    # Validators

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(PhenotypicFeature, field)
        return field


@dataclass(config=PydanticConfig)
class EntityToDiseaseAssociationMixin(EntityToFeatureOrDiseaseQualifiersMixin):
    """
    mixin class for any association whose object (target node) is a disease
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["object"]

    object: Union[Curie, Disease] = None

    # Validators

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(Disease, field)
        return field


@dataclass(config=PydanticConfig)
class DiseaseOrPhenotypicFeatureToEntityAssociationMixin:

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[Curie, DiseaseOrPhenotypicFeature] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(DiseaseOrPhenotypicFeature, field)
        return field


@dataclass(config=PydanticConfig)
class DiseaseOrPhenotypicFeatureAssociationToLocationAssociation(
    Association, DiseaseOrPhenotypicFeatureToEntityAssociationMixin
):

    # Class Variables
    _category: ClassVar[str] = "DiseaseOrPhenotypicFeatureAssociationToLocationAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "relation", "object"]

    object: Union[Curie, AnatomicalEntity] = None

    # Validators

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(AnatomicalEntity, field)
        return field


@dataclass(config=PydanticConfig)
class DiseaseOrPhenotypicFeatureToLocationAssociation(
    Association, DiseaseOrPhenotypicFeatureToEntityAssociationMixin
):
    """
    An association between either a disease or a phenotypic feature and an anatomical entity, where the
    disease/feature manifests in that site.
    """

    # Class Variables
    _category: ClassVar[str] = "DiseaseOrPhenotypicFeatureToLocationAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "relation", "object"]

    object: Union[Curie, AnatomicalEntity] = None

    # Validators

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(AnatomicalEntity, field)
        return field


@dataclass(config=PydanticConfig)
class EntityToDiseaseOrPhenotypicFeatureAssociationMixin:

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["object"]

    object: Union[Curie, DiseaseOrPhenotypicFeature] = None

    # Validators

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(DiseaseOrPhenotypicFeature, field)
        return field


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

    # Class Variables
    _category: ClassVar[str] = "CellLineToDiseaseOrPhenotypicFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "object", "relation", "subject"]

    subject: Union[Curie, DiseaseOrPhenotypicFeature] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(DiseaseOrPhenotypicFeature, field)
        return field


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

    # Class Variables
    _category: ClassVar[str] = "ChemicalToDiseaseOrPhenotypicFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "relation", "object"]

    object: Union[Curie, DiseaseOrPhenotypicFeature] = None

    # Validators

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(DiseaseOrPhenotypicFeature, field)
        return field


@dataclass(config=PydanticConfig)
class MaterialSampleToDiseaseOrPhenotypicFeatureAssociation(
    Association,
    MaterialSampleToEntityAssociationMixin,
    EntityToDiseaseOrPhenotypicFeatureAssociationMixin,
):
    """
    An association between a material sample and a disease or phenotype.
    """

    # Class Variables
    _category: ClassVar[str] = "MaterialSampleToDiseaseOrPhenotypicFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "object", "relation"]


@dataclass(config=PydanticConfig)
class GenotypeToEntityAssociationMixin:

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[Curie, Genotype] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(Genotype, field)
        return field


@dataclass(config=PydanticConfig)
class GenotypeToPhenotypicFeatureAssociation(
    Association, EntityToPhenotypicFeatureAssociationMixin, GenotypeToEntityAssociationMixin
):
    """
    Any association between one genotype and a phenotypic feature, where having the genotype confers the phenotype,
    either in isolation or through environment
    """

    # Class Variables
    _category: ClassVar[str] = "GenotypeToPhenotypicFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "object", "relation", "predicate", "subject"]

    predicate: Curie = None
    subject: Union[Curie, Genotype] = None

    # Validators

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(Genotype, field)
        return field


@dataclass(config=PydanticConfig)
class ExposureEventToPhenotypicFeatureAssociation(
    Association, EntityToPhenotypicFeatureAssociationMixin
):
    """
    Any association between an environment and a phenotypic feature, where being in the environment influences the
    phenotype.
    """

    # Class Variables
    _category: ClassVar[str] = "ExposureEventToPhenotypicFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "object", "relation", "subject"]

    subject: Union[str, ExposureEvent] = None


@dataclass(config=PydanticConfig)
class DiseaseToPhenotypicFeatureAssociation(
    Association, EntityToPhenotypicFeatureAssociationMixin, DiseaseToEntityAssociationMixin
):
    """
    An association between a disease and a phenotypic feature in which the phenotypic feature is associated with the
    disease in some way.
    """

    # Class Variables
    _category: ClassVar[str] = "DiseaseToPhenotypicFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "object", "relation"]


@dataclass(config=PydanticConfig)
class CaseToPhenotypicFeatureAssociation(
    Association, EntityToPhenotypicFeatureAssociationMixin, CaseToEntityAssociationMixin
):
    """
    An association between a case (e.g. individual patient) and a phenotypic feature in which the individual has or
    has had the phenotype.
    """

    # Class Variables
    _category: ClassVar[str] = "CaseToPhenotypicFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "object", "relation"]


@dataclass(config=PydanticConfig)
class BehaviorToBehavioralFeatureAssociation(
    Association, EntityToPhenotypicFeatureAssociationMixin
):
    """
    An association between an aggregate behavior and a behavioral feature manifested by the individual exhibited or
    has exhibited the behavior.
    """

    # Class Variables
    _category: ClassVar[str] = "BehaviorToBehavioralFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    subject: Union[Curie, Behavior] = None
    object: Union[Curie, BehavioralFeature] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(Behavior, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(BehavioralFeature, field)
        return field


@dataclass(config=PydanticConfig)
class GeneToEntityAssociationMixin:

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[str, GeneOrGeneProduct] = None


@dataclass(config=PydanticConfig)
class VariantToEntityAssociationMixin:

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[Curie, SequenceVariant] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(SequenceVariant, field)
        return field


@dataclass(config=PydanticConfig)
class GeneToPhenotypicFeatureAssociation(
    Association, EntityToPhenotypicFeatureAssociationMixin, GeneToEntityAssociationMixin
):

    # Class Variables
    _category: ClassVar[str] = "GeneToPhenotypicFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "object", "relation", "subject"]

    subject: Union[str, GeneOrGeneProduct] = None


@dataclass(config=PydanticConfig)
class GeneToDiseaseAssociation(
    Association, EntityToDiseaseAssociationMixin, GeneToEntityAssociationMixin
):

    # Class Variables
    _category: ClassVar[str] = "GeneToDiseaseAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "object", "relation", "subject"]

    subject: Union[str, GeneOrGeneProduct] = None


@dataclass(config=PydanticConfig)
class VariantToGeneAssociation(Association, VariantToEntityAssociationMixin):
    """
    An association between a variant and a gene, where the variant has a genetic association with the gene (i.e. is in
    linkage disequilibrium)
    """

    # Class Variables
    _category: ClassVar[str] = "VariantToGeneAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "relation", "object", "predicate"]

    object: Union[Curie, Gene] = None
    predicate: Curie = None

    # Validators

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(Gene, field)
        return field

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class VariantToGeneExpressionAssociation(VariantToGeneAssociation, GeneExpressionMixin):
    """
    An association between a variant and expression of a gene (i.e. e-QTL)
    """

    # Class Variables
    _category: ClassVar[str] = "VariantToGeneExpressionAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "relation", "object", "predicate"]

    predicate: Curie = None

    # Validators

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class VariantToPopulationAssociation(
    Association, VariantToEntityAssociationMixin, FrequencyQuantifier, FrequencyQualifierMixin
):
    """
    An association between a variant and a population, where the variant has particular frequency in the population
    """

    # Class Variables
    _category: ClassVar[str] = "VariantToPopulationAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    subject: Union[Curie, SequenceVariant] = None
    object: Union[Curie, PopulationOfIndividualOrganisms] = None
    has_quotient: Optional[float] = None
    has_count: Optional[int] = None
    has_total: Optional[int] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(SequenceVariant, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(PopulationOfIndividualOrganisms, field)
        return field


@dataclass(config=PydanticConfig)
class PopulationToPopulationAssociation(Association):
    """
    An association between a two populations
    """

    # Class Variables
    _category: ClassVar[str] = "PopulationToPopulationAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    subject: Union[Curie, PopulationOfIndividualOrganisms] = None
    object: Union[Curie, PopulationOfIndividualOrganisms] = None
    predicate: Curie = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(PopulationOfIndividualOrganisms, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(PopulationOfIndividualOrganisms, field)
        return field

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class VariantToPhenotypicFeatureAssociation(
    Association, VariantToEntityAssociationMixin, EntityToPhenotypicFeatureAssociationMixin
):

    # Class Variables
    _category: ClassVar[str] = "VariantToPhenotypicFeatureAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "object", "relation", "subject"]

    subject: Union[Curie, SequenceVariant] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(SequenceVariant, field)
        return field


@dataclass(config=PydanticConfig)
class VariantToDiseaseAssociation(
    Association, VariantToEntityAssociationMixin, EntityToDiseaseAssociationMixin
):

    # Class Variables
    _category: ClassVar[str] = "VariantToDiseaseAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "predicate", "object"]

    subject: Union[Curie, NamedThing] = None
    predicate: Curie = None
    object: Union[Curie, NamedThing] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(NamedThing, field)
        return field

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(NamedThing, field)
        return field


@dataclass(config=PydanticConfig)
class GenotypeToDiseaseAssociation(
    Association, GenotypeToEntityAssociationMixin, EntityToDiseaseAssociationMixin
):

    # Class Variables
    _category: ClassVar[str] = "GenotypeToDiseaseAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "predicate", "object"]

    subject: Union[Curie, NamedThing] = None
    predicate: Curie = None
    object: Union[Curie, NamedThing] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(NamedThing, field)
        return field

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(NamedThing, field)
        return field


@dataclass(config=PydanticConfig)
class ModelToDiseaseAssociationMixin:
    """
    This mixin is used for any association class for which the subject (source node) plays the role of a 'model', in
    that it recapitulates some features of the disease in a way that is useful for studying the disease outside a
    patient carrying the disease
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["subject", "predicate"]

    subject: Union[Curie, NamedThing] = None
    predicate: Curie = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(NamedThing, field)
        return field

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class GeneAsAModelOfDiseaseAssociation(
    GeneToDiseaseAssociation, ModelToDiseaseAssociationMixin, EntityToDiseaseAssociationMixin
):

    # Class Variables
    _category: ClassVar[str] = "GeneAsAModelOfDiseaseAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "object", "relation", "subject"]

    subject: Union[str, GeneOrGeneProduct] = None


@dataclass(config=PydanticConfig)
class VariantAsAModelOfDiseaseAssociation(
    VariantToDiseaseAssociation, ModelToDiseaseAssociationMixin, EntityToDiseaseAssociationMixin
):

    # Class Variables
    _category: ClassVar[str] = "VariantAsAModelOfDiseaseAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "predicate", "object", "subject"]

    subject: Union[Curie, SequenceVariant] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(SequenceVariant, field)
        return field


@dataclass(config=PydanticConfig)
class GenotypeAsAModelOfDiseaseAssociation(
    GenotypeToDiseaseAssociation, ModelToDiseaseAssociationMixin, EntityToDiseaseAssociationMixin
):

    # Class Variables
    _category: ClassVar[str] = "GenotypeAsAModelOfDiseaseAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "predicate", "object", "subject"]

    subject: Union[Curie, Genotype] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(Genotype, field)
        return field


@dataclass(config=PydanticConfig)
class CellLineAsAModelOfDiseaseAssociation(
    CellLineToDiseaseOrPhenotypicFeatureAssociation,
    ModelToDiseaseAssociationMixin,
    EntityToDiseaseAssociationMixin,
):

    # Class Variables
    _category: ClassVar[str] = "CellLineAsAModelOfDiseaseAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "object", "relation", "subject"]

    subject: Union[Curie, CellLine] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(CellLine, field)
        return field


@dataclass(config=PydanticConfig)
class OrganismalEntityAsAModelOfDiseaseAssociation(
    Association, ModelToDiseaseAssociationMixin, EntityToDiseaseAssociationMixin
):

    # Class Variables
    _category: ClassVar[str] = "OrganismalEntityAsAModelOfDiseaseAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "object", "relation", "subject"]

    subject: Union[Curie, OrganismalEntity] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(OrganismalEntity, field)
        return field


@dataclass(config=PydanticConfig)
class GeneHasVariantThatContributesToDiseaseAssociation(GeneToDiseaseAssociation):

    # Class Variables
    _category: ClassVar[str] = "GeneHasVariantThatContributesToDiseaseAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "object", "relation", "subject"]

    subject: Union[str, GeneOrGeneProduct] = None
    sequence_variant_qualifier: Optional[Union[Curie, SequenceVariant]] = None

    # Validators

    @validator('sequence_variant_qualifier')
    def check_sequence_variant_qualifier_prefix(cls, field):
        check_curie_prefix(SequenceVariant, field)
        return field


@dataclass(config=PydanticConfig)
class GeneToExpressionSiteAssociation(Association):
    """
    An association between a gene and an expression site, possibly qualified by stage/timing info.
    """

    # Class Variables
    _category: ClassVar[str] = "GeneToExpressionSiteAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    subject: Union[str, GeneOrGeneProduct] = None
    object: Union[Curie, AnatomicalEntity] = None
    predicate: Curie = None
    stage_qualifier: Optional[Union[Curie, LifeStage]] = None
    quantifier_qualifier: Optional[Union[str, OntologyClass]] = None

    # Validators

    @validator('stage_qualifier')
    def check_stage_qualifier_prefix(cls, field):
        check_curie_prefix(LifeStage, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(AnatomicalEntity, field)
        return field

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class SequenceVariantModulatesTreatmentAssociation(Association):
    """
    An association between a sequence variant and a treatment or health intervention. The treatment object itself
    encompasses both the disease and the drug used.
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    subject: Union[Curie, SequenceVariant] = None
    object: Union[Curie, Treatment] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(SequenceVariant, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(Treatment, field)
        return field


@dataclass(config=PydanticConfig)
class FunctionalAssociation(Association):
    """
    An association between a macromolecular machine mixin (gene, gene product or complex of gene products) and either
    a molecular activity, a biological process or a cellular location in which a function is executed.
    """

    # Class Variables
    _category: ClassVar[str] = "FunctionalAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    subject: Union[str, MacromolecularMachineMixin] = None
    object: Union[str, GeneOntologyClass] = None


@dataclass(config=PydanticConfig)
class MacromolecularMachineToEntityAssociationMixin:
    """
    an association which has a macromolecular machine mixin as a subject
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[Curie, NamedThing] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(NamedThing, field)
        return field


@dataclass(config=PydanticConfig)
class MacromolecularMachineToMolecularActivityAssociation(
    FunctionalAssociation, MacromolecularMachineToEntityAssociationMixin
):
    """
    A functional association between a macromolecular machine (gene, gene product or complex) and a molecular activity
    (as represented in the GO molecular function branch), where the entity carries out the activity, or contributes to
    its execution.
    """

    # Class Variables
    _category: ClassVar[str] = "MacromolecularMachineToMolecularActivityAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    object: Union[Curie, MolecularActivity] = None

    # Validators

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(MolecularActivity, field)
        return field


@dataclass(config=PydanticConfig)
class MacromolecularMachineToBiologicalProcessAssociation(
    FunctionalAssociation, MacromolecularMachineToEntityAssociationMixin
):
    """
    A functional association between a macromolecular machine (gene, gene product or complex) and a biological process
    or pathway (as represented in the GO biological process branch), where the entity carries out some part of the
    process, regulates it, or acts upstream of it.
    """

    # Class Variables
    _category: ClassVar[str] = "MacromolecularMachineToBiologicalProcessAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    object: Union[Curie, BiologicalProcess] = None

    # Validators

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(BiologicalProcess, field)
        return field


@dataclass(config=PydanticConfig)
class MacromolecularMachineToCellularComponentAssociation(
    FunctionalAssociation, MacromolecularMachineToEntityAssociationMixin
):
    """
    A functional association between a macromolecular machine (gene, gene product or complex) and a cellular component
    (as represented in the GO cellular component branch), where the entity carries out its function in the cellular
    component.
    """

    # Class Variables
    _category: ClassVar[str] = "MacromolecularMachineToCellularComponentAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    object: Union[Curie, CellularComponent] = None

    # Validators

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(CellularComponent, field)
        return field


@dataclass(config=PydanticConfig)
class GeneToGoTermAssociation(FunctionalAssociation):

    # Class Variables
    _category: ClassVar[str] = "GeneToGoTermAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    subject: Union[Curie, MolecularEntity] = None
    object: Union[str, GeneOntologyClass] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(MolecularEntity, field)
        return field


@dataclass(config=PydanticConfig)
class SequenceAssociation(Association):
    """
    An association between a sequence feature and a genomic entity it is localized to.
    """

    # Class Variables
    _category: ClassVar[str] = "SequenceAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "subject", "predicate", "object", "relation"]


@dataclass(config=PydanticConfig)
class GenomicSequenceLocalization(SequenceAssociation):
    """
    A relationship between a sequence feature and a genomic entity it is localized to. The reference entity may be a
    chromosome, chromosome region or information entity such as a contig.
    """

    # Class Variables
    _category: ClassVar[str] = "GenomicSequenceLocalization"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    subject: Union[Curie, GenomicEntity] = None
    object: Union[Curie, GenomicEntity] = None
    predicate: Curie = None
    start_interbase_coordinate: Optional[int] = None
    end_interbase_coordinate: Optional[int] = None
    genome_build: Optional[str] = None
    strand: Optional[str] = None
    phase: Optional[str] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(GenomicEntity, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(GenomicEntity, field)
        return field

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class SequenceFeatureRelationship(Association):
    """
    For example, a particular exon is part of a particular transcript or gene
    """

    # Class Variables
    _category: ClassVar[str] = "SequenceFeatureRelationship"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    subject: Union[Curie, GenomicEntity] = None
    object: Union[Curie, GenomicEntity] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(GenomicEntity, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(GenomicEntity, field)
        return field


@dataclass(config=PydanticConfig)
class TranscriptToGeneRelationship(SequenceFeatureRelationship):
    """
    A gene is a collection of transcripts
    """

    # Class Variables
    _category: ClassVar[str] = "TranscriptToGeneRelationship"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    subject: Union[Curie, Transcript] = None
    object: Union[Curie, Gene] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(Transcript, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(Gene, field)
        return field


@dataclass(config=PydanticConfig)
class GeneToGeneProductRelationship(SequenceFeatureRelationship):
    """
    A gene is transcribed and potentially translated to a gene product
    """

    # Class Variables
    _category: ClassVar[str] = "GeneToGeneProductRelationship"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    subject: Union[Curie, Gene] = None
    object: Union[str, GeneProductMixin] = None
    predicate: Curie = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(Gene, field)
        return field

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class ExonToTranscriptRelationship(SequenceFeatureRelationship):
    """
    A transcript is formed from multiple exons
    """

    # Class Variables
    _category: ClassVar[str] = "ExonToTranscriptRelationship"
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    subject: Union[Curie, Exon] = None
    object: Union[Curie, Transcript] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(Exon, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(Transcript, field)
        return field


@dataclass(config=PydanticConfig)
class GeneRegulatoryRelationship(Association):
    """
    A regulatory relationship between two genes
    """

    # Class Variables
    _category: ClassVar[str] = "GeneRegulatoryRelationship"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "predicate", "subject", "object"]

    predicate: Curie = None
    subject: Union[str, GeneOrGeneProduct] = None
    object: Union[str, GeneOrGeneProduct] = None

    # Validators

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class AnatomicalEntityToAnatomicalEntityAssociation(Association):

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    subject: Union[Curie, AnatomicalEntity] = None
    object: Union[Curie, AnatomicalEntity] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(AnatomicalEntity, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(AnatomicalEntity, field)
        return field


@dataclass(config=PydanticConfig)
class AnatomicalEntityToAnatomicalEntityPartOfAssociation(
    AnatomicalEntityToAnatomicalEntityAssociation
):
    """
    A relationship between two anatomical entities where the relationship is mereological, i.e the two entities are
    related by parthood. This includes relationships between cellular components and cells, between cells and tissues,
    tissues and whole organisms
    """

    # Class Variables
    _category: ClassVar[str] = "AnatomicalEntityToAnatomicalEntityPartOfAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    subject: Union[Curie, AnatomicalEntity] = None
    object: Union[Curie, AnatomicalEntity] = None
    predicate: Curie = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(AnatomicalEntity, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(AnatomicalEntity, field)
        return field

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class AnatomicalEntityToAnatomicalEntityOntogenicAssociation(
    AnatomicalEntityToAnatomicalEntityAssociation
):
    """
    A relationship between two anatomical entities where the relationship is ontogenic, i.e. the two entities are
    related by development. A number of different relationship types can be used to specify the precise nature of the
    relationship.
    """

    # Class Variables
    _category: ClassVar[str] = "AnatomicalEntityToAnatomicalEntityOntogenicAssociation"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    subject: Union[Curie, AnatomicalEntity] = None
    object: Union[Curie, AnatomicalEntity] = None
    predicate: Curie = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(AnatomicalEntity, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(AnatomicalEntity, field)
        return field

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class OrganismTaxonToEntityAssociation:
    """
    An association between an organism taxon and another entity
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["subject"]

    subject: Union[Curie, OrganismTaxon] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(OrganismTaxon, field)
        return field


@dataclass(config=PydanticConfig)
class OrganismTaxonToOrganismTaxonAssociation(Association, OrganismTaxonToEntityAssociation):
    """
    A relationship between two organism taxon nodes
    """

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["id", "predicate", "relation", "subject", "object"]

    subject: Union[Curie, OrganismTaxon] = None
    object: Union[Curie, OrganismTaxon] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(OrganismTaxon, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(OrganismTaxon, field)
        return field


@dataclass(config=PydanticConfig)
class OrganismTaxonToOrganismTaxonSpecialization(OrganismTaxonToOrganismTaxonAssociation):
    """
    A child-parent relationship between two taxa. For example: Homo sapiens subclass_of Homo
    """

    # Class Variables
    _category: ClassVar[str] = "OrganismTaxonToOrganismTaxonSpecialization"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    subject: Union[Curie, OrganismTaxon] = None
    object: Union[Curie, OrganismTaxon] = None
    predicate: Curie = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(OrganismTaxon, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(OrganismTaxon, field)
        return field

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class OrganismTaxonToOrganismTaxonInteraction(OrganismTaxonToOrganismTaxonAssociation):
    """
    An interaction relationship between two taxa. This may be a symbiotic relationship (encompassing mutualism and
    parasitism), or it may be non-symbiotic. Example: plague transmitted_by flea; cattle domesticated_by Homo sapiens;
    plague infects Homo sapiens
    """

    # Class Variables
    _category: ClassVar[str] = "OrganismTaxonToOrganismTaxonInteraction"
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    subject: Union[Curie, OrganismTaxon] = None
    object: Union[Curie, OrganismTaxon] = None
    predicate: Curie = None
    associated_environmental_context: Optional[str] = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(OrganismTaxon, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(OrganismTaxon, field)
        return field

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


@dataclass(config=PydanticConfig)
class OrganismTaxonToEnvironmentAssociation(Association, OrganismTaxonToEntityAssociation):

    # Class Variables
    _required_attributes: ClassVar[List[str]] = ["id", "relation", "subject", "object", "predicate"]

    subject: Union[Curie, OrganismTaxon] = None
    object: Union[Curie, NamedThing] = None
    predicate: Curie = None

    # Validators

    @validator('subject')
    def check_subject_prefix(cls, field):
        check_curie_prefix(OrganismTaxon, field)
        return field

    @validator('object')
    def check_object_prefix(cls, field):
        check_curie_prefix(NamedThing, field)
        return field

    @validator('predicate')
    def check_predicate_prefix(cls, field):
        check_curie_prefix(cls, field)
        return field


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
