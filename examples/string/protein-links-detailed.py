import re
import uuid

from biolink_model_pydantic.model import PairwiseGeneToGeneInteraction, Predicate, Protein

from koza.cli_runner import koza_app

for row in koza_app.source:

    protein_a = Protein(id='ENSEMBL:' + re.sub(r'\d+\.', '', row['protein1']))
    protein_b = Protein(id='ENSEMBL:' + re.sub(r'\d+\.', '', row['protein2']))

    pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction(
        id="uuid:" + str(uuid.uuid1()),
        subject=protein_a.id,
        object=protein_b.id,
        predicate=Predicate.interacts_with,
        relation=koza_app.translation_table.global_table['interacts with'],
    )

    koza_app.write(protein_a, protein_b, pairwise_gene_to_gene_interaction)
