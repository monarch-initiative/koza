import os

from biolink_model.datamodel.pydanticmodel_v2 import Disease, Gene

from koza.io.writer.tsv_writer import TSVWriter


def test_tsv_writer():
    """
    Writes a test tsv file
    """
    g = Gene(id="HGNC:11603", name="TBX4")
    d = Disease(id="MONDO:0005002", name="chronic obstructive pulmonary disease")

    ent = [g, d]

    node_properties = [
        'id',
        'category',
        'symbol',
        'in_taxon',
        'provided_by',
        'source',
        'has_biological_sequence',
        'iri',
        'type',
        'xref',
        'description',
        'synonym',
        'in_taxon_label',
        'deprecated',
        'full_name',
        'name',
        'has_attribute'
    ]

    outdir = "output/tests"
    outfile = "tsvwriter-node-only"

    t = TSVWriter(outdir, outfile, node_properties)
    t.write(ent)
    t.finalize()

    assert os.path.exists("{}/{}_nodes.tsv".format(outdir, outfile))
