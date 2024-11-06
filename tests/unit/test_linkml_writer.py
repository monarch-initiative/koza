import uuid

import pytest
from unittest.mock import mock_open, patch

from biolink_model.datamodel.pydanticmodel_v2 import GeneToPhenotypicFeatureAssociation
from linkml_runtime import SchemaView
import importlib

from pyparsing import pyparsing_test

from koza.io.writer.linkml_writer import LinkMLWriter
from koza.model.config.source_config import OutputFormat


# setup the tests by creating a schemaview for biolink model

@pytest.fixture
def sv():
    return SchemaView(importlib.resources.files("biolink_model.schema").joinpath("biolink_model.yaml"))

@pytest.fixture
def d2p_writer(sv):
    return LinkMLWriter(
        output_dir=".",
        filename="test.tsv",
        schemaview=sv,
        class_names=["DiseaseToPhenotypicFeatureAssociation"]
        )

def test_get_slot_names(d2p_writer):
    expected_slot_subset = ['id', 'category', 'subject', 'predicate', 'object', 'frequency_qualifier', 'has_total', 'has_count', 'has_percentage', 'qualifiers', 'primary_knowledge_source', 'aggregator_knowledge_source']
    missing_slots = set(expected_slot_subset) - set(d2p_writer.slots)
    assert not missing_slots, f"Missing slots: {missing_slots}"

@pytest.mark.parametrize(
    "value, class_name", [
        ("GeneToDiseaseAssociation", "gene to disease association"),
        ("gene to disease association", "gene to disease association")
    ]
)
def test_get_class(d2p_writer, value, class_name):
    assert d2p_writer.get_class(value).name == class_name

def test_get_output_format(d2p_writer):
    assert d2p_writer.get_output_format("test.tsv") == OutputFormat.tsv
    assert d2p_writer.get_output_format("test.jsonl") == OutputFormat.jsonl

# test the write method using a mock file handle
# @pytest.mark.skip # this is
def test_write(d2p_writer):
    mock_file = mock_open()
    d2p_writer.fh = mock_file()
    with patch("builtins.open", mock_file):
        d2p_writer.write(GeneToPhenotypicFeatureAssociation(
            id="1",
            subject='MONDO:0005148',
            predicate='biolink:has_phenotype',
            object='HP:0007354',
            primary_knowledge_source='infores:hpo-annotations',
            knowledge_level='not_provided',
            agent_type='not_provided'
        ))
        d2p_writer.finalize()

        # assert the expected header
        written_lines = mock_file().write.call_args_list
        written_header = written_lines[0][0][0].replace('\n','').split('\t')
        # publications, qualifiers and type are not actually used, their presence here comes from kgx/biolink assumptions in build_export_row that need to be fixed
        assert written_header == ['id', 'category', 'subject', 'predicate', 'object', 'agent_type', 'knowledge_level', 'primary_knowledge_source', 'publications', 'qualifiers','type']
        # assert the expected data row
        written_data_row = written_lines[1][0][0].replace('\n','').split('\t')
        assert written_data_row == ['1', 'biolink:GeneToPhenotypicFeatureAssociation', 'MONDO:0005148', 'biolink:has_phenotype', 'HP:0007354', 'not_provided', 'not_provided', 'infores:hpo-annotations', '', '', '']
