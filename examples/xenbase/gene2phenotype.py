import uuid

from biolink_model_pydantic.model import Gene, PhenotypicFeature, GeneToPhenotypicFeatureAssociation, Predicate


def transform(row, translate_table=None, maps=None):
    gene = Gene(id='Xenbase:' + row['SUBJECT'])

    phenotype = PhenotypicFeature(id=row['OBJECT'])

    association = GeneToPhenotypicFeatureAssociation(
        id="uuid:" + str(uuid.uuid1()),
        subject=gene.id,
        predicate=Predicate.has_phenotype,
        object=phenotype.id,
        relation=row['RELATION'].replace('_', ':')
    )

    if row['SOURCE']:
        association.publications = [row['SOURCE']]

    return gene, association, phenotype
