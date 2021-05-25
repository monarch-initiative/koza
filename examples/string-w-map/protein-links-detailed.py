from koza.model.biolink import Gene, PairwiseGeneToGeneInteraction, predicate
from koza.manager.data_provider import inject_row, inject_translation_table, inject_map
from koza.manager.data_collector import collect

source_name = 'protein-links-detailed'

row = inject_row(source_name)
translation_table = inject_translation_table()
entrez_2_string = inject_map('entrez_2_string')

gene_a = Gene()
gene_b = Gene()

pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction()

# TODO: remove the all uppercase NCBIGENE curie prefix once the curie prefix validation is fixed upstream

#gene_a.id = 'NCBIGene:' + entrez_2_string[row['protein1']]['entrez']
#gene_b.id = 'NCBIGene:' + entrez_2_string[row['protein2']]['entrez']
gene_a.id = 'NCBIGENE:' + entrez_2_string[row['protein1']]['entrez']
gene_b.id = 'NCBIGENE:' + entrez_2_string[row['protein2']]['entrez']

pairwise_gene_to_gene_interaction.subject = gene_a
pairwise_gene_to_gene_interaction.object = gene_b
pairwise_gene_to_gene_interaction.predicate = predicate.interacts_with
# pairwise_gene_to_gene_interaction.relation = translation_table.global_table['interacts with']
pairwise_gene_to_gene_interaction.relation = 'RO:0002436'

collect(source_name, gene_a, gene_b, pairwise_gene_to_gene_interaction)
