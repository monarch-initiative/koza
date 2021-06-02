import re

from koza.model.biolink.model import Protein, PairwiseGeneToGeneInteraction, Predicate
from koza.koza_runner import get_koza_app

koza = get_koza_app()

source_name = 'protein-links-detailed'

for row in koza.file_registry[source_name]:

    protein_a = Protein()
    protein_b = Protein()

    pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction()

    protein_a.id = 'ENSEMBL:' + re.sub(r'\d+\.', '', row['protein1'])
    protein_b.id = 'ENSEMBL:' + re.sub(r'\d+\.', '', row['protein2'])

    pairwise_gene_to_gene_interaction.subject = protein_a
    pairwise_gene_to_gene_interaction.object = protein_b
    pairwise_gene_to_gene_interaction.predicate = Predicate.interacts_with

    koza.write(source_name, [protein_a, protein_b, pairwise_gene_to_gene_interaction])
