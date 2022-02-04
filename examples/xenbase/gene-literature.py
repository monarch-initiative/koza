import logging
import uuid

from biolink_model_pydantic.model import (
    Gene,
    InformationContentEntityToNamedThingAssociation,
    Predicate,
    Publication,
)

from koza.cli_runner import koza_app

LOG = logging.getLogger(__name__)

source_name = 'gene-literature'

row = koza_app.get_row(source_name)
genepage2gene = koza_app.get_map('genepage-2-gene')

entities = []

gene_pages = row['gene_pages']

publication = Publication(
    id='PMID:' + row['pmid'], type=koza_app.translation_table.resolve_term("publication")
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

        association = InformationContentEntityToNamedThingAssociation(
            id="uuid:" + str(uuid.uuid1()),
            subject=publication.id,
            object=gene.id,
            predicate=Predicate.mentions,
            relation="IAO:0000142",  # Mentions
        )

        entities.append(association)

koza_app.write(*entities)
