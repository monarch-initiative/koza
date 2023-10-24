import re
import uuid

from biolink.pydanticmodel import PairwiseGeneToGeneInteraction, Protein

from koza.cli_runner import get_koza_app

koza_app = get_koza_app('protein-links-detailed')

for row in koza_app.source:
    protein_a = Protein(id='ENSEMBL:' + re.sub(r'\d+\.', '', row['protein1']))
    protein_b = Protein(id='ENSEMBL:' + re.sub(r'\d+\.', '', row['protein2']))

    pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction(
        id="uuid:" + str(uuid.uuid1()),
        subject=protein_a.id,
        object=protein_b.id,
        predicate="biolink:interacts_with",
    )

    koza_app.write(protein_a, protein_b, pairwise_gene_to_gene_interaction)
