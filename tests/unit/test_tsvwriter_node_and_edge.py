import os
from biolink_model_pydantic.model import Gene, Disease, GeneToDiseaseAssociation, Predicate
from koza.io.writer.tsv_writer import TSVWriter

def test_tsv_writer():
    """
    Writes a test tsv file
    """
    g = Gene(id="HGNC:11603", name="TBX4")
    d = Disease(id="MONDO:0005002", name="chronic obstructive pulmonary disease")
    a = GeneToDiseaseAssociation(id="uuid:5b06e86f-d768-4cd9-ac27-abe31e95ab1e",
                                subject=g.id,
                                object=d.id,
                                relation="RO:0003304",
                                predicate=Predicate.contributes_to,
                                )
    ent = [g, d, a]

    node_properties = ['id','category','symbol','in_taxon','provided_by','source']
    edge_properties = ['id','subject','predicate','object','category','relation','qualifiers','publications','provided_by','source']

    outdir = "test-output"
    outfile = "tsvwriter-node-and-edge"

    t = TSVWriter(outdir, outfile, node_properties, edge_properties)
    t.write(ent)
    t.finalize()

    assert os.path.exists("{}/{}_nodes.tsv".format(outdir, outfile)) and os.path.exists("{}/{}_edges.tsv".format(outdir, outfile))