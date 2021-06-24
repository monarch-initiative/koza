import re
import uuid

from biolink_model_pydantic.model import Protein, PairwiseGeneToGeneInteraction, Predicate
from koza.manager.data_provider import inject_row, inject_translation_table
from koza.manager.data_collector import write

source_name = 'protein-links-detailed'

row = inject_row(source_name)
translation_table = inject_translation_table()

protein_a = Protein(id='ENSEMBL:' + re.sub(r'\d+\.', '', row['protein1']))
protein_b = Protein(id='ENSEMBL:' + re.sub(r'\d+\.', '', row['protein2']))

pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction(
    id="uuid:" + str(uuid.uuid1()),
    subject=protein_a.id,
    object=protein_b.id,
    predicate=Predicate.interacts_with,
    relation = translation_table.global_table['interacts with'],
)

write(source_name, protein_a, protein_b, pairwise_gene_to_gene_interaction)
