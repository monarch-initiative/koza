from koza.model import Gene, PairwiseGeneToGeneInteraction, predicate
from koza.facade.data_provider import inject_files, inject_translation_table
from koza.facade.data_collector import serialize
from koza.facade.helper import next_row

_ingest_name = 'protein-links-detailed'

file, entrez_2_string, = inject_files(_ingest_name)
translation_table = inject_translation_table(_ingest_name)

gene_a = Gene()
gene_b = Gene()

pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction(provided_by='stringdb')

model = (gene_a, gene_b, pairwise_gene_to_gene_interaction)


gene_a.id = 'NCBIGene:' + entrez_2_string[file['protein1']]['entrez']
gene_b.id = 'NCBIGene:' + entrez_2_string[file['protein2']]['entrez']

pairwise_gene_to_gene_interaction.subject = gene_a
pairwise_gene_to_gene_interaction.object = gene_b
pairwise_gene_to_gene_interaction.predicate = predicate.interacts_with
pairwise_gene_to_gene_interaction.relation = translation_table.global_table['interacts with']

serialize(*model)
