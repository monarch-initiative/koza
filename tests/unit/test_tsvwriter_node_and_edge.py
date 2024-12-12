from pathlib import Path

from biolink_model.datamodel.pydanticmodel_v2 import (Disease, Gene,
                                                      GeneToDiseaseAssociation)
from koza.io.writer.tsv_writer import TSVWriter
from koza.model.config.source_config import WriterConfig


def test_tsv_writer():
    """
    Writes a test tsv file
    """
    node_properties = [
        "id",
        "category",
        "symbol",
        "in_taxon",
        "provided_by",
        "source",
    ]

    edge_properties = [
        "id",
        "subject",
        "predicate",
        "object",
        "category" "qualifiers",
        "has_count",
        "has_total",
        "publications",
        "provided_by",
    ]

    config = WriterConfig(node_properties=node_properties, edge_properties=edge_properties)

    gene = Gene(id="HGNC:11603", in_taxon=["NCBITaxon:9606"], symbol="TBX4")
    disease = Disease(id="MONDO:0005002", name="chronic obstructive pulmonary disease")
    association = GeneToDiseaseAssociation(
        id="uuid:5b06e86f-d768-4cd9-ac27-abe31e95ab1e",
        subject=gene.id,
        object=disease.id,
        predicate="biolink:contributes_to",
        knowledge_level="not_provided",
        agent_type="not_provided",
        has_count=0,
        has_total=20,
    )
    entities = [gene, disease, association]

    outdir = "output/tests"
    source_name = "tsvwriter-node-and-edge"

    t = TSVWriter(outdir, source_name, config=config)
    t.write(entities)
    t.finalize()

    nodes_path = Path(f"{outdir}/{source_name}_nodes.tsv")
    edges_path = Path(f"{outdir}/{source_name}_edges.tsv")

    assert nodes_path.exists()
    assert edges_path.exists()

    # read the node and edges tsv files and confirm the expected values
    with nodes_path.open("r") as fh:
        lines = fh.readlines()
        assert lines[1] == "HGNC:11603\tbiolink:Gene\t\tNCBITaxon:9606\t\tTBX4\n"
        assert len(lines) == 3

    with edges_path.open("r") as fh:
        lines = fh.readlines()
        assert (
            lines[1].strip()
            == "uuid:5b06e86f-d768-4cd9-ac27-abe31e95ab1e\tHGNC:11603\tbiolink:contributes_to\tMONDO:0005002\t\t\t0\t20"
        )
        assert len(lines) == 2
