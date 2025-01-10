import uuid

from biolink_model.datamodel.pydanticmodel_v2 import Gene, PairwiseGeneToGeneInteraction

from koza.runner import KozaTransform

def transform_record(koza: KozaTransform, record: dict):
    a = record["protein1"]
    b = record["protein2"]
    mapped_a = koza.lookup(a, "entrez")
    mapped_b = koza.lookup(b, "entrez")
    gene_a = Gene(id="NCBIGene:" + mapped_a)
    gene_b = Gene(id="NCBIGene:" + mapped_b)

    pairwise_gene_to_gene_interaction = PairwiseGeneToGeneInteraction(
        id="uuid:" + str(uuid.uuid1()),
        subject=gene_a.id,
        object=gene_b.id,
        predicate="biolink:interacts_with",
        knowledge_level="not_provided",
        agent_type="not_provided",
    )

    koza.write(gene_a, gene_b, pairwise_gene_to_gene_interaction)
