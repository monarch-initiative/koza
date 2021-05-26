import logging

from koza.manager.data_provider import inject_row, inject_map, inject_translation_table
from koza.manager.data_collector import collect
from koza.model.biolink import Gene

LOG = logging.getLogger(__name__)

source_name = 'gene-information'
prefix = 'Xenbase:'

row = inject_row(source_name)
translation_table = inject_translation_table()
genepage2gene = inject_map('genepage-2-gene')

entities = []

gene_page_id = row['gene_page_id']
gene_symbol = row['gene_symbol']
gene_name = row['gene_name']
gene_synonyms = row['gene_synonyms'].split('|') if row['gene_synonyms'] else []

gene_ids = [
    genepage2gene[gene_page_id]['tropicalis_id'],
    genepage2gene[gene_page_id]['laevis_l_id'],
    genepage2gene[gene_page_id]['laevis_s_id'],
]

for gene_id in gene_ids:
    gene = Gene()
    gene.id = prefix + gene_id
    gene.name = gene_name
    gene.symbol = gene_symbol
    gene.synonym = gene_synonyms
    entities.append(gene)

collect(source_name, *entities)
