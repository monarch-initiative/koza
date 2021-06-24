import logging
import uuid

from koza.manager.data_provider import inject_row, inject_map, inject_translation_table
from koza.manager.data_collector import write
from biolink_model_pydantic.model import Publication, Gene, NamedThingToInformationContentEntityAssociation, Predicate

LOG = logging.getLogger(__name__)

source_name = 'gene-literature'

row = inject_row(source_name)
translation_table = inject_translation_table()
genepage2gene = inject_map('genepage-2-gene')

entities = []

gene_pages = row['gene_pages']

publication = Publication(
    id='PMID:' + row['pmid'],
    type=translation_table.resolve_term("publication")
)

entities.append(publication)

for gene_page in gene_pages.split(','):
    gene_page_id = gene_page.split(' ')[0]
    try:
        gene_ids = map(lambda id: f"Xenbase:{id}", list(genepage2gene[gene_page_id].values()))
    except KeyError:
        LOG.debug(f"Could not locate genepage_id: {gene_page_id} in row {row}")
        continue
    for gene_id in gene_ids:
        gene = Gene(id=gene_id)

        entities.append(gene)

        association = NamedThingToInformationContentEntityAssociation(
            id="uuid:" + str(uuid.uuid1()),
            subject=gene.id,
            predicate=Predicate.mentions,
            object=publication.id,
            relation="IAO:0000142"  # Mentions
        )

        entities.append(association)

write(source_name, *entities)
