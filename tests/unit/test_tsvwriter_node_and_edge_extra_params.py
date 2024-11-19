import re

import pytest
from biolink_model.datamodel.pydanticmodel_v2 import Disease, Gene, GeneToDiseaseAssociation

from koza.io.writer.tsv_writer import TSVWriter


def test_tsv_writer_extra_node_params():
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
        'description',
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
    expected_message = "Extra fields found in row: ['in_taxon']"
    with pytest.raises(ValueError, match=re.escape(expected_message)):
        t.write(ent)


def test_tsv_writer_extra_edge_params():
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
    ]

    outdir = "output/tests"
    outfile = "tsvwriter-node-and-edge"

    t = TSVWriter(outdir, outfile, node_properties, edge_properties, check_fields=True)
    expected_message = "Extra fields found in row: ['description']"
    with pytest.raises(ValueError, match=re.escape(expected_message)):
        t.write(ent)
