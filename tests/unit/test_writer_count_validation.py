"""Tests for writer node/edge count-bound enforcement (min/max_{node,edge}_count)."""

import pytest
from biolink_model.datamodel.pydanticmodel_v2 import Disease, Gene, VariantToPopulationAssociation

import koza
from koza.io.writer.jsonl_writer import JSONLWriter
from koza.io.writer.tsv_writer import TSVWriter
from koza.model.writer import WriterConfig
from koza.runner import KozaRunner, KozaTransform, KozaTransformHooks
from koza.utils.exceptions import CountValidationError

NODE_PROPERTIES = ["id", "category", "symbol"]
EDGE_PROPERTIES = ["id", "subject", "predicate", "object", "category"]


def _entities():
    gene = Gene(id="HGNC:11603", symbol="TBX4")
    disease = Disease(id="MONDO:0005002", name="chronic obstructive pulmonary disease")
    association = VariantToPopulationAssociation(
        id="uuid:5b06e86f-d768-4cd9-ac27-abe31e95ab1e",
        subject=gene.id,
        object=disease.id,
        predicate="biolink:contributes_to",
        knowledge_level="not_provided",
        agent_type="not_provided",
    )
    return [gene, disease, association]


def _write(writer):
    writer.write(_entities())
    writer.finalize()


def test_counts_track_written_rows(tmp_path):
    config = WriterConfig(node_properties=NODE_PROPERTIES, edge_properties=EDGE_PROPERTIES)
    writer = TSVWriter(tmp_path, "counts", config=config)
    _write(writer)
    assert writer.node_count == 2
    assert writer.edge_count == 1


def test_min_edge_count_violation_raises(tmp_path):
    config = WriterConfig(
        node_properties=NODE_PROPERTIES,
        edge_properties=EDGE_PROPERTIES,
        min_edge_count=100,
    )
    writer = TSVWriter(tmp_path, "counts", config=config)
    _write(writer)
    with pytest.raises(CountValidationError, match="edge count 1 is below the configured min_edge_count of 100"):
        writer.validate_counts()


def test_min_node_count_violation_raises(tmp_path):
    config = WriterConfig(
        node_properties=NODE_PROPERTIES,
        edge_properties=EDGE_PROPERTIES,
        min_node_count=100,
    )
    writer = TSVWriter(tmp_path, "counts", config=config)
    _write(writer)
    with pytest.raises(CountValidationError, match="node count 2 is below the configured min_node_count of 100"):
        writer.validate_counts()


def test_max_edge_count_violation_raises(tmp_path):
    config = WriterConfig(
        node_properties=NODE_PROPERTIES,
        edge_properties=EDGE_PROPERTIES,
        max_edge_count=0,
    )
    writer = TSVWriter(tmp_path, "counts", config=config)
    _write(writer)
    with pytest.raises(CountValidationError, match="edge count 1 is above the configured max_edge_count of 0"):
        writer.validate_counts()


def test_counts_within_bounds_pass(tmp_path):
    config = WriterConfig(
        node_properties=NODE_PROPERTIES,
        edge_properties=EDGE_PROPERTIES,
        min_node_count=1,
        min_edge_count=1,
        max_node_count=10,
        max_edge_count=10,
    )
    writer = TSVWriter(tmp_path, "counts", config=config)
    _write(writer)
    writer.validate_counts()  # should not raise


def test_no_bounds_configured_is_noop(tmp_path):
    config = WriterConfig(node_properties=NODE_PROPERTIES, edge_properties=EDGE_PROPERTIES)
    writer = TSVWriter(tmp_path, "counts", config=config)
    _write(writer)
    writer.validate_counts()  # no bounds set -> no-op


def test_jsonl_writer_counts_and_enforces(tmp_path):
    config = WriterConfig(min_edge_count=100)
    writer = JSONLWriter(str(tmp_path), "counts", config=config)
    _write(writer)
    assert writer.node_count == 2
    assert writer.edge_count == 1
    with pytest.raises(CountValidationError, match="min_edge_count"):
        writer.validate_counts()


def test_runner_run_enforces_min_edge_count(tmp_path):
    """End-to-end: KozaRunner.run() must raise when the writer falls short of min_edge_count."""
    config = WriterConfig(edge_properties=EDGE_PROPERTIES, min_edge_count=100)
    writer = TSVWriter(tmp_path, "counts", config=config)

    @koza.transform_record()
    def transform_record(koza_transform: KozaTransform, record):
        koza_transform.write(
            VariantToPopulationAssociation(
                id="uuid:5b06e86f-d768-4cd9-ac27-abe31e95ab1e",
                subject="HGNC:11603",
                object="MONDO:0005002",
                predicate="biolink:contributes_to",
                knowledge_level="not_provided",
                agent_type="not_provided",
            )
        )

    runner = KozaRunner(
        data=[{"a": 1}],
        writer=writer,
        hooks=KozaTransformHooks(transform_record=[transform_record]),
    )
    with pytest.raises(CountValidationError, match="min_edge_count"):
        runner.run()


def test_multiple_violations_reported_together(tmp_path):
    config = WriterConfig(
        node_properties=NODE_PROPERTIES,
        edge_properties=EDGE_PROPERTIES,
        min_node_count=100,
        min_edge_count=100,
    )
    writer = TSVWriter(tmp_path, "counts", config=config)
    _write(writer)
    with pytest.raises(CountValidationError) as exc:
        writer.validate_counts()
    message = str(exc.value)
    assert "min_node_count" in message
    assert "min_edge_count" in message
