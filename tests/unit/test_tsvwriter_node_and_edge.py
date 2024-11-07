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
        "provided_by",
        "source",
        'has_biological_sequence',
        'type',
        'xref',
        'description',
        'in_taxon_label',
        'synonym',
        'deprecated',
        'has_attribute',
        'full_name',
        'iri', 'name',
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
        'subject_category',
        'object_direction_qualifier',
        'sex_qualifier',
        'negated',
        'has_percentage',
        'aggregator_knowledge_source',
        'has_evidence',
        'qualified_predicate',
        'qualifiers',
        'object_category',
        'timepoint',
        'subject_label_closure',
        'agent_type',
        'has_attribute',
        'category',
        'original_predicate',
        'iri',
        'frequency_qualifier',
        'type',
        'subject_namespace',
        'subject_closure',
        'object_label_closure',
        'object_namespace',
        'original_object',
        'subject_category_closure',
        'name',
        'has_quotient',
        'knowledge_level',
        'knowledge_source',
        'description',
        'subject_direction_qualifier',
        'deprecated',
        'original_subject',
        'object_category_closure',
        'qualifier',
        'retrieval_source_ids',
        'primary_knowledge_source',
        'object_aspect_qualifier',
        'object_closure',
        'subject_aspect_qualifier'
    ]

    outdir = "output/tests"
    outfile = "tsvwriter-node-and-edge"

    t = TSVWriter(outdir, outfile, node_properties, edge_properties)
    t.write(ent)
    t.finalize()

    assert os.path.exists("{}/{}_nodes.tsv".format(outdir, outfile)) and os.path.exists(
        "{}/{}_edges.tsv".format(outdir, outfile)
    )

    # read the node and edges tsv files and confirm the expected values
    with open("{}/{}_nodes.tsv".format(outdir, outfile), "r") as f:
        lines = f.readlines()
        # assert lines[1] == "HGNC:11603\tbiolink:Gene\t\tNCBITaxon:9606\t\tTBX4\n"
        assert lines[1] == "HGNC:11603\tbiolink:Gene\t\t\t\t\t\t\t\t\t\tNCBITaxon:9606\t\t\t\tTBX4\t\n"
        assert len(lines) == 3

    with open("{}/{}_edges.tsv".format(outdir, outfile), "r") as f:
        lines = f.readlines()
        assert (
            lines[1].strip()
            == "uuid:5b06e86f-d768-4cd9-ac27-abe31e95ab1e\tHGNC:11603\tbiolink:contributes_to\tMONDO:0005002\t" +
                "biolink:GeneToDiseaseAssociation\t\tnot_provided\t\t\t\t\t\t\t0\t\t\t\t20\t\tnot_provided"
        )
        assert len(lines) == 2
