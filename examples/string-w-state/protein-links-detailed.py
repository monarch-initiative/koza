import re
import uuid

from biolink_model.datamodel.pydanticmodel_v2 import PairwiseGeneToGeneInteraction, Protein

import koza


@koza.on_data_begin()
def init(koza: koza.KozaTransform):
    koza.state["counter"] = 0

@koza.transform()
def string_transform(koza: koza.KozaTransform):
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
        koza.state["counter"] += 1

@koza.on_data_end()
def end(koza: koza.KozaTransform):
    koza.log(f"Total records: {koza.state['counter']}")
