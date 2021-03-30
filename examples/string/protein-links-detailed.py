from koza.model import Protein, PairwiseGeneToGeneInteraction, predicate
from koza.facade.data_provider import inject_files, inject_translation_table
from koza.facade.data_collector import serialize

_ingest_name = 'protein-links-detailed'

file, = inject_files(_ingest_name)
translation_table = inject_translation_table(_ingest_name)

protein_a = Protein()
protein_b = Protein()

pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction(provided_by='stringdb')

model = (protein_a, protein_b, pairwise_gene_to_gene_interaction)


protein_a.id = 'Ensembl:' + file['protein1']
protein_b.id = 'Ensembl:' + file['protein2']

pairwise_gene_to_gene_interaction.subject = protein_a
pairwise_gene_to_gene_interaction.object = protein_b
pairwise_gene_to_gene_interaction.predicate = predicate.interacts_with
pairwise_gene_to_gene_interaction.relation = translation_table.global_table['interacts with']

serialize(*model)
