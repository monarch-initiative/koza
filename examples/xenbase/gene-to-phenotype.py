from koza.model.biolink import Gene, PhenotypicFeature, GeneToPhenotypicFeatureAssociation, predicate
from koza.manager.data_provider import inject_row, inject_translation_table
from koza.manager.data_collector import collect

source_name = 'gene-to-phenotype'

row = inject_row(source_name)
translation_table = inject_translation_table()

gene = Gene()
gene.id = 'Xenbase:' + row['SUBJECT']

phenotype = PhenotypicFeature()
phenotype.id = row['OBJECT']

association = GeneToPhenotypicFeatureAssociation()
association.subject = gene.id
association.predicate = predicate.has_phenotype
association.object = phenotype.id
association.relation = row['RELATION'].replace('_', ':')

collect(source_name, gene, association, phenotype)
