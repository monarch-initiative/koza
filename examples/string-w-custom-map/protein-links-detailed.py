import uuid

from biolink_model_pydantic.model import Gene, PairwiseGeneToGeneInteraction, Predicate

from koza.cli_runner import koza_app

row = koza_app.get_row()
entrez_2_string = koza_app.get_map('custom-entrez-2-string')

gene_a = Gene(id='NCBIGene:' + entrez_2_string[row['protein1']]['entrez'])
gene_b = Gene(id='NCBIGene:' + entrez_2_string[row['protein2']]['entrez'])

pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction(
    id="uuid:" + str(uuid.uuid1()),
    subject=gene_a.id,
    object=gene_b.id,
    predicate=Predicate.interacts_with,
    relation=koza_app.translation_table.global_table['interacts with'],
)

koza_app.write(gene_a, gene_b, pairwise_gene_to_gene_interaction)
