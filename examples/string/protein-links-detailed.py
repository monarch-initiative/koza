import re
import uuid

from biolink_model.datamodel.pydanticmodel_v2 import PairwiseGeneToGeneInteraction, Protein
from koza.model.graphs import KnowledgeGraph

import koza


@koza.transform()
def string_transform(koza: koza.KozaTransform, data):
    for row in data:
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

        yield KnowledgeGraph(nodes=[protein_a, protein_b], edges=[pairwise_gene_to_gene_interaction])
