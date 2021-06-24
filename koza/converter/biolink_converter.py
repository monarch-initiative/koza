from biolink_model_pydantic.model import Gene

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
