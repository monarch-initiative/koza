import os
from biolink_model_pydantic.model import Gene, Disease, GeneToDiseaseAssociation, Predicate
from koza.io.writer.tsv_writer import TSVWriter

def test_tsv_writer():
    """
    Writes a test tsv file
    """
    g = Gene(id="HGNC:11603", name="TBX4")
    d = Disease(id="MONDO:0005002", name="chronic obstructive pulmonary disease")

    ent = [g, d]

    node_properties = ['id','category','symbol','in_taxon','provided_by','source']
    
    outdir = "test-output"
    outfile = "tsvwriter-node-only"

    t = TSVWriter(outdir, outfile, node_properties)
    t.write(ent)
    t.finalize()

    assert os.path.exists("{}/{}_nodes.tsv".format(outdir, outfile))