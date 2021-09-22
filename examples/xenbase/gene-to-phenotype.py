import uuid

from biolink_model_pydantic.model import (
    Gene,
    GeneToPhenotypicFeatureAssociation,
    PhenotypicFeature,
    Predicate,
)

from koza.cli_runner import koza_app

row = koza_app.get_row()

gene = Gene(id='Xenbase:' + row['SUBJECT'])

phenotype = PhenotypicFeature(id=row['OBJECT'])

association = GeneToPhenotypicFeatureAssociation(
    id="uuid:" + str(uuid.uuid1()),
    subject=gene.id,
    predicate=Predicate.has_phenotype,
    object=phenotype.id,
    relation=row['RELATION'].replace('_', ':'),
)

if row['SOURCE']:
    association.publications = [row['SOURCE']]

koza_app.write(gene, association, phenotype)
