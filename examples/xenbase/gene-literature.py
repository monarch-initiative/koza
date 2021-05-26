import logging

from koza.manager.data_provider import inject_row, inject_map, inject_translation_table
from koza.manager.data_collector import collect
from koza.model.biolink import Publication, Gene

LOG = logging.getLogger(__name__)

source_name = 'gene-literature'

row = inject_row(source_name)
translation_table = inject_translation_table()
genepage2gene = inject_map('genepage-to-gene')

entities = []

gene_pages = row['gene_pages']

publication = Publication()
publication.id = 'PMID:' + row['pmid']

entities.append(publication)

for gene_page in gene_pages.split(','):
    gene_page_id = gene_page.split(' ')[0]
    try:
        gene_ids = genepage2gene[gene_page_id]
    except KeyError:
        LOG.debug(f"Could not locate genepage_id: {gene_page_id} in row {row}")
        continue
    for gene_id in gene_ids:
        gene = Gene()
        gene.id = gene_id

        # TODO: publications seem to have relationships to associations, not sure what association
        # TODO: to use to simply say that the publication mentions the gene

        entities.append(gene)

collect(entities)
