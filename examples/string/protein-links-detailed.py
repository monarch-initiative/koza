import re
import uuid

from biolink_model_pydantic.model import Protein, PairwiseGeneToGeneInteraction, Predicate
from koza.manager.data_collector import collect

from koza.koza_runner import get_koza_app

koza = get_koza_app()

source_name = 'protein-links-detailed'

for row in koza.file_registry[source_name]:

    protein_a = Protein(id='ENSEMBL:' + re.sub(r'\d+\.', '', row['protein1']))
    protein_b = Protein(id='ENSEMBL:' + re.sub(r'\d+\.', '', row['protein2']))

    pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction(
        id="uuid:" + str(uuid.uuid1()),
        subject=protein_a.id,
        object=protein_b.id,
        predicate=Predicate.interacts_with,
        # relation = translation_table.global_table['interacts with'],
        relation='IAO:0002436'
    )

    collect(source_name, protein_a, protein_b, pairwise_gene_to_gene_interaction)
