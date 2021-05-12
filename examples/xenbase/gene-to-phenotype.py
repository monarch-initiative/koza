from koza.model.biolink import Gene
from koza.manager.data_provider import inject_row, inject_translation_table
from koza.manager.data_collector import collect

source_name = 'gene-to-phenotype'

row = inject_row(source_name)
translation_table = inject_translation_table()

gene = Gene()
gene.id = 'xenbase:' + row['SUBJECT']

collect(gene)