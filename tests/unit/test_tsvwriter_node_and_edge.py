import os

from biolink_model.datamodel.pydanticmodel_v2 import Disease, Gene, GeneToDiseaseAssociation

from koza.io.writer.tsv_writer import TSVWriter


def test_tsv_writer():
    """
    Writes a test tsv file
    """
    g = Gene(id="HGNC:11603", name="TBX4")
    d = Disease(id="MONDO:0005002", name="chronic obstructive pulmonary disease")
    a = GeneToDiseaseAssociation(
        id="uuid:5b06e86f-d768-4cd9-ac27-abe31e95ab1e",
        subject=g.id,
        object=d.id,
        predicate="biolink:contributes_to",
        knowledge_level="not_provided",
        agent_type="not_provided",
    )
    ent = [g, d, a]

    node_properties = ["id", "category", "symbol", "in_taxon", "provided_by", "source"]
    edge_properties = ["id", "subject", "predicate", "object", "category" "qualifiers", "publications", "provided_by"]

    outdir = "output/tests"
    outfile = "tsvwriter-node-and-edge"

    t = TSVWriter(outdir, outfile, node_properties, edge_properties)
    t.write(ent)
    t.finalize()

    assert os.path.exists("{}/{}_nodes.tsv".format(outdir, outfile)) and os.path.exists(
        "{}/{}_edges.tsv".format(outdir, outfile)
    )
