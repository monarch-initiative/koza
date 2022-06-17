import uuid

from biolink_model_pydantic.model import Gene, PairwiseGeneToGeneInteraction

from koza.cli_runner import get_koza_app

source_name = 'map-protein-links-detailed'
map_name = 'entrez-2-string'

koza_app = get_koza_app(source_name)
row = koza_app.get_row()
koza_map = koza_app.get_map(map_name)

gene_a = Gene(id='NCBIGene:' + koza_map[row['protein1']]['entrez'])
gene_b = Gene(id='NCBIGene:' + koza_map[row['protein2']]['entrez'])

pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction(
    id="uuid:" + str(uuid.uuid1()),
    subject=gene_a.id,
    object=gene_b.id,
    predicate="biolink:interacts_with"
)

koza_app.write(gene_a, gene_b, pairwise_gene_to_gene_interaction)
