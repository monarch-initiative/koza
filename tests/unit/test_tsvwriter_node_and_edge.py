import os

from biolink_model.datamodel.pydanticmodel_v2 import Disease, Gene, GeneToDiseaseAssociation

from koza.io.writer.tsv_writer import TSVWriter


def test_tsv_writer():
    """
    Writes a test tsv file
    """
    g = Gene(id="HGNC:11603", in_taxon=["NCBITaxon:9606"], symbol="TBX4")
    d = Disease(id="MONDO:0005002", name="chronic obstructive pulmonary disease")
    a = GeneToDiseaseAssociation(
        id="uuid:5b06e86f-d768-4cd9-ac27-abe31e95ab1e",
        subject=g.id,
        object=d.id,
        predicate="biolink:contributes_to",
        knowledge_level="not_provided",
        agent_type="not_provided",
        has_count=0,
        has_total=20,
    )

    ent = [g, d, a]

    node_properties = [
        "id",
        "category",
        "symbol",
        "in_taxon",
        'description',
        'name',
    ]
    edge_properties = [
        "id",
        "subject",
        "predicate",
        "object",
        "category" "qualifiers",
        "has_count",
        "has_total",
        'agent_type',
        'category',
        'knowledge_level',
    ]

    outdir = "output/tests"
    outfile = "tsvwriter-node-and-edge"

    t = TSVWriter(outdir, outfile, node_properties, edge_properties, check_fields=True)
    t.write(ent)
    t.finalize()

    assert os.path.exists("{}/{}_nodes.tsv".format(outdir, outfile)) and os.path.exists(
        "{}/{}_edges.tsv".format(outdir, outfile)
    )

    # read the node and edges tsv files and confirm the expected values
    with open("{}/{}_nodes.tsv".format(outdir, outfile), "r") as f:
        lines = f.readlines()
        # assert lines[1] == "HGNC:11603\tbiolink:Gene\t\tNCBITaxon:9606\t\tTBX4\n"
        assert lines[1] == "HGNC:11603\tbiolink:Gene\t\t\tNCBITaxon:9606\tTBX4\n"
        assert len(lines) == 3

    with open("{}/{}_edges.tsv".format(outdir, outfile), "r") as f:
        lines = f.readlines()
        assert (
            lines[1].strip()
            == "uuid:5b06e86f-d768-4cd9-ac27-abe31e95ab1e\tHGNC:11603\tbiolink:contributes_to\tMONDO:0005002\t"
            + "biolink:GeneToDiseaseAssociation\tnot_provided\t\t0\t20\tnot_provided"
        )
        assert len(lines) == 2
