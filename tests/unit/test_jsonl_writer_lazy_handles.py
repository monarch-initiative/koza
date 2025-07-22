import tempfile
from unittest.mock import mock_open, patch

from biolink_model.datamodel.pydanticmodel_v2 import Disease, Gene, GeneToDiseaseAssociation, KnowledgeLevelEnum, AgentTypeEnum

from koza.io.writer.jsonl_writer import JSONLWriter
from koza.model.writer import WriterConfig


def test_jsonl_writer_lazy_file_handle_creation():
    """
    Test that JSONLWriter creates file handles lazily when write() is called,
    not during __init__, preventing null handle exceptions.
    """
    config = WriterConfig()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        writer = JSONLWriter(temp_dir, "test", config)
        
        # Verify file handles don't exist after init
        assert not hasattr(writer, "nodeFH")
        assert not hasattr(writer, "edgeFH")
        
        # Create test entities that will generate both nodes and edges
        gene = Gene(id="HGNC:11603", symbol="TBX4")
        disease = Disease(id="MONDO:0005002", name="test disease")
        association = GeneToDiseaseAssociation(
            id="uuid:test",
            subject=gene.id,
            object=disease.id,
            predicate="biolink:contributes_to",
            knowledge_level=KnowledgeLevelEnum.not_provided,
            agent_type=AgentTypeEnum.not_provided,
        )
        
        entities = [gene, disease, association]
        
        # Mock the open function to track file handle creation
        with patch("builtins.open", mock_open()) as mock_file:
            writer.write(entities)
            
            # Verify file handles were created during write()
            assert hasattr(writer, "nodeFH")
            assert hasattr(writer, "edgeFH")
            
            # Verify open was called for both node and edge files
            assert mock_file.call_count == 2
            mock_file.assert_any_call(f"{temp_dir}/test_nodes.jsonl", "w")
            mock_file.assert_any_call(f"{temp_dir}/test_edges.jsonl", "w")