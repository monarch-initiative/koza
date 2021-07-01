import uuid

from biolink_model_pydantic.model import (
    Gene,
    GeneToPhenotypicFeatureAssociation,
    PhenotypicFeature,
    Predicate,
)

from koza.manager.data_provider import inject_curie_cleaner


def gpi2gene(row: dict) -> Gene:
    """
    Convert from Gene Product Information format to biolink:Gene instance

    http://geneontology.org/docs/gene-product-information-gpi-format/

    :param row: Dictionary representing a single GPI file row
    :return: biolink:Gene model representing the GPI row
    """

    curie_cleaner = inject_curie_cleaner()

    xrefs = []
    if row["DB_Xref(s)"]:
        xrefs = [curie_cleaner.clean(xref) for xref in row["DB_Xref(s)"].split("|")]

    gene = Gene(
        id=row['DB_Object_ID'],
        symbol=row['DB_Object_Symbol'],
        name=row['DB_Object_Name'],
        synonym=row['DB_Object_Synonym(s)'].split("|") if row['DB_Object_Synonym(s)'] else [],
        in_taxon=curie_cleaner.clean(row['Taxon']),
        xref=xrefs,
        source=row['DB'],
    )

    return gene


def phaf2gene(row: dict, gene_id_prefix=None, taxon_id_prefix=None) -> Gene:

    id = row['Gene systematic ID']
    if gene_id_prefix:
        id = gene_id_prefix + id
    taxon = row['Taxon']
    if taxon:
        taxon = taxon_id_prefix + taxon

    gene = Gene(id=id)
    if taxon:
        gene.in_taxon = taxon
    # It appears symbols are stored in the name field
    if row['Gene name']:
        gene.symbol = row['Gene name']

    return gene


def phaf2phenotype(row: dict) -> PhenotypicFeature:
    return PhenotypicFeature(id=row['FYPO ID'])


def phaf2gene_pheno_association(
    row, gene, phenotype, relation
) -> GeneToPhenotypicFeatureAssociation:

    return GeneToPhenotypicFeatureAssociation(
        id="uuid:" + str(uuid.uuid1()),
        subject=gene.id,
        predicate=Predicate.has_phenotype,
        object=phenotype.id,
        relation=relation,
        publications=[row['Reference']],
    )
