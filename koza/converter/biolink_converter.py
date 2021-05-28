from koza.model.biolink import Gene


def gpi2gene(row: dict) -> Gene:
    """
    Convert from Gene Product Information format to biolink:Gene instance

    http://geneontology.org/docs/gene-product-information-gpi-format/

    :param row: Dictionary representing a single GPI file row
    :return: biolink:Gene model representing the GPI row
    """
    gene = Gene()

    gene.source = row['DB']
    gene.id = row['DB_Object_ID']
    gene.symbol = row['DB_Object_Symbol']
    gene.name = row['DB_Object_Name']
    gene.synonym = row['DB_Object_Synonym(s)'].split("|") if row['DB_Object_Synonym(s)'] else []
    gene.in_taxon = [row['Taxon'].replace("taxon:", "NCBITaxon:")]
    gene.xref = row['DB_Xref(s)'].split("|") if row['DB_Xref(s)'] else []

    return gene
