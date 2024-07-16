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


def test_tsv_writer_split():
    """
    Writes a test tsv file
    """
    g1 = Gene(id="HGNC:11603", name="TBX4", category=["biolink:Gene"])
    d1 = Disease(id="MONDO:0005002", name="chronic obstructive pulmonary disease", category=["biolink:Disease"])
    a1 = GeneToDiseaseAssociation(
        id="uuid:5b06e86f-d768-4cd9-ac27-abe31e95ab1e",
        subject=g1.id,
        object=d1.id,
        predicate="biolink:contributes_to",
        knowledge_level="not_provided",
        agent_type="not_provided",
        subject_category="biolink:Gene",
        object_category="biolink:Disease",
    )
    g2 = Gene(id="HGNC:11604", name="TBX5", category=["biolink:Gene"])
    d2 = Disease(id="MONDO:0005003", name="asthma")
    a2 = GeneToDiseaseAssociation(
        id="uuid:5b06e86f-d768-4cd9-ac27-abe31e95ab1f",
        subject=g2.id,
        object=d2.id,
        predicate="biolink:contributes_to",
        knowledge_level="not_provided",
        agent_type="not_provided",
    )
    g3 = Gene(id="HGNC:11605", name="TBX6")
    d3 = Disease(id="MONDO:0005004", name="lung cancer", category=["biolink:Disease"])
    a3 = GeneToDiseaseAssociation(
        id="uuid:5b06e86f-d768-4cd9-ac27-abe31e95ab1g",
        subject=g3.id,
        object=d3.id,
        predicate="biolink:contributes_to",
        knowledge_level="not_provided",
        agent_type="not_provided",
    )
    g4 = Gene(id="HGNC:11606", name="TBX7")
    d4 = Disease(id="MONDO:0005005", name="pulmonary fibrosis")
    a4 = GeneToDiseaseAssociation(
        id="uuid:5b06e86f-d768-4cd9-ac27-abe31e95ab1h",
        subject=g4.id,
        object=d4.id,
        predicate="biolink:contributes_to",
        knowledge_level="not_provided",
        agent_type="not_provided",
    )

    ents = [[g1, d1, a1], [g2, d2, a2], [g3, d3, a3], [g4, d4, a4]]

    node_properties = ["id", "category", "symbol", "in_taxon", "provided_by", "source"]
    edge_properties = ["id", "subject", "predicate", "object", "category" "qualifiers", "publications", "provided_by"]

    outdir = "output/tests/split-examples"
    outfile = "tsvwriter"
    split_edge_file_substring = "UnknownCategoryGeneToDiseaseAssociationUnknownCategory"

    t = TSVWriter(outdir, outfile, node_properties, edge_properties)
    for ent in ents:
        t.write(ent, split=True)

    t.finalize()

    assert os.path.exists("{}/splits/{}_Disease_nodes.tsv".format(outdir, outfile))
    assert os.path.exists("{}/splits/{}_{}_edges.tsv".format(outdir, outfile, split_edge_file_substring))
    assert os.path.exists("{}/splits/{}_Gene_nodes.tsv".format(outdir, outfile))

    assert os.path.exists("{}/{}_nodes.tsv".format(outdir, outfile)) and os.path.exists(
        "{}/{}_edges.tsv".format(outdir, outfile)
    )
