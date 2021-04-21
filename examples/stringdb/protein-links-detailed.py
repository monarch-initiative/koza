import re

from koza.model.biolink import Protein, PairwiseGeneToGeneInteraction, predicate
from koza.koza_runner import get_koza_app

koza = get_koza_app()

for row in koza.file_registry['protein-links-detailed']:

    protein_a = Protein()
    protein_b = Protein()

    pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction()

    protein_a.id = 'ENSEMBL:' + re.sub(r'\d+\.', '', row['protein1'])
    protein_b.id = 'ENSEMBL:' + re.sub(r'\d+\.', '', row['protein2'])

    pairwise_gene_to_gene_interaction.subject = protein_a
    pairwise_gene_to_gene_interaction.object = protein_b
    pairwise_gene_to_gene_interaction.predicate = predicate.interacts_with

    koza.write(protein_a, protein_b, pairwise_gene_to_gene_interaction)
