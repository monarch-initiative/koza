import os

from biolink_model.datamodel.pydanticmodel_v2 import Disease, Gene

from koza.io.writer.tsv_writer import TSVWriter
from koza.model.writer import WriterConfig


def test_tsv_writer():
    """
    Writes a test tsv file
    """
    gene = Gene(id="HGNC:11603", name="TBX4")
    disease = Disease(id="MONDO:0005002", name="chronic obstructive pulmonary disease")

    entities = [gene, disease]

    node_properties = ['id', 'category', 'symbol', 'in_taxon', 'provided_by', 'source']

    config = WriterConfig(node_properties=node_properties)

    outdir = "output/tests"
    source_name = "tsvwriter-node-only"

    t = TSVWriter(outdir, source_name, config=config)
    t.write(entities)
    t.finalize()

    assert os.path.exists(f"{outdir}/{source_name}_nodes.tsv")
    assert not os.path.exists(f"{outdir}/{source_name}_edges.tsv")
