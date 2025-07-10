import re
import uuid

from biolink_model.datamodel.pydanticmodel_v2 import PairwiseGeneToGeneInteraction, Protein

from koza.runner import KozaTransform


def transform(koza: KozaTransform):
    for row in koza.data:
        protein_a = Protein(id="ENSEMBL:" + re.sub(r"\d+\.", "", row["protein1"]))
        protein_b = Protein(id="ENSEMBL:" + re.sub(r"\d+\.", "", row["protein2"]))

        pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction(
            id="uuid:" + str(uuid.uuid1()),
            subject=protein_a.id,
            object=protein_b.id,
            predicate="biolink:interacts_with",
            knowledge_level="not_provided",
            agent_type="not_provided",
        )

        koza.write(protein_a, protein_b, pairwise_gene_to_gene_interaction)
