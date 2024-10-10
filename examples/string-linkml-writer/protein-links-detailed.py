import uuid

from biolink_model.datamodel.pydanticmodel_v2 import PairwiseGeneToGeneInteraction, Gene

from koza.cli_utils import get_koza_app

koza_app = get_koza_app('protein-links-detailed')
koza_map = koza_app.get_map('entrez-2-string')

while (row := koza_app.get_row()) is not None:
    gene_a = Gene(id="NCBIGene:" + koza_map[row["protein1"]]["entrez"])
    gene_b = Gene(id="NCBIGene:" + koza_map[row["protein2"]]["entrez"])

    pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction(
        id="uuid:" + str(uuid.uuid1()),
        subject=gene_a.id,
        object=gene_b.id,
        predicate="biolink:interacts_with",
        knowledge_level="not_provided",
        agent_type="not_provided",
    )
    koza_app.write(gene_a, gene_b, writer="nodes")
    koza_app.write(pairwise_gene_to_gene_interaction, writer="edges")
    koza_app.write()
