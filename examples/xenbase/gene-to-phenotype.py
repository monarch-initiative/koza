import uuid

from biolink_model_pydantic.model import Gene, PhenotypicFeature, GeneToPhenotypicFeatureAssociation, Predicate
from koza.manager.data_provider import inject_row, inject_translation_table
from koza.manager.data_collector import collect

source_name = 'gene-to-phenotype'

row = inject_row(source_name)
translation_table = inject_translation_table()

gene = Gene(id='Xenbase:' + row['SUBJECT'])

phenotype = PhenotypicFeature(id=row['OBJECT'])

association = GeneToPhenotypicFeatureAssociation(
    id="uuid:" + str(uuid.uuid1()),
    subject=gene.id,
    predicate=Predicate.has_phenotype,
    object=phenotype.id,
    relation=row['RELATION'].replace('_', ':')
)

collect(source_name, gene, association, phenotype)
