import uuid

from biolink.pydanticmodel_v2 import Gene, PairwiseGeneToGeneInteraction

from koza.cli_runner import get_koza_app

source_name = 'custom-map-protein-links-detailed'
koza_app = get_koza_app(source_name)
row = koza_app.get_row()
entrez_2_string = koza_app.get_map('custom-entrez-2-string')

gene_a = Gene(id='NCBIGene:' + entrez_2_string[row['protein1']]['entrez'])
gene_b = Gene(id='NCBIGene:' + entrez_2_string[row['protein2']]['entrez'])

pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction(
    id="uuid:" + str(uuid.uuid1()), subject=gene_a.id, object=gene_b.id, predicate="biolink:interacts_with"
)

koza_app.write(gene_a, gene_b, pairwise_gene_to_gene_interaction)
