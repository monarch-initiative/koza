from koza.model import Gene, PairwiseGeneToGeneInteraction, predicate
from koza.manager.data_provider import inject_file, inject_translation_table
from koza.manager.data_collector import serialize
from koza.manager.helper import next_row

_ingest_name = 'protein-links-detailed'

file, entrez_2_string, = inject_file(_ingest_name)
translation_table = inject_translation_table(_ingest_name)

gene_a = Gene()  # Maps to file['protein1']
gene_b = Gene()  # Maps to file['protein2']

pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction(provided_by='stringdb')

model = (gene_a, gene_b, pairwise_gene_to_gene_interaction)


serialize(_ingest_name, *model)
