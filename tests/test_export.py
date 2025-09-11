"""
Test suite for export functionality including archive and compression.
"""

import pytest
import tempfile
import tarfile
import gzip
from pathlib import Path
from unittest.mock import patch, MagicMock

from koza.graph_operations.utils import GraphDatabase
from koza.model.graph_operations import KGXFormat


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_database(temp_dir):
    """Create a sample database with nodes and edges for testing."""
    db_path = temp_dir / "test.duckdb"
    
    with GraphDatabase(db_path) as db:
        # Create sample nodes table
        db.conn.execute("""
            CREATE TABLE nodes (
                id VARCHAR,
                category VARCHAR,
                name VARCHAR,
                provided_by VARCHAR
            )
        """)
        
        db.conn.execute("""
            INSERT INTO nodes VALUES
                ('HGNC:123', 'biolink:Gene', 'gene1', 'hgnc'),
                ('HGNC:456', 'biolink:Gene', 'gene2', 'hgnc'),
                ('MONDO:001', 'biolink:Disease', 'disease1', 'mondo')
        """)
        
        # Create sample edges table
        db.conn.execute("""
            CREATE TABLE edges (
                subject VARCHAR,
                predicate VARCHAR,
                object VARCHAR,
                category VARCHAR,
                provided_by VARCHAR
            )
        """)
        
        db.conn.execute("""
            INSERT INTO edges VALUES
                ('HGNC:123', 'biolink:related_to', 'MONDO:001', 'biolink:Association', 'string'),
                ('HGNC:456', 'biolink:causes', 'MONDO:001', 'biolink:Association', 'omim')
        """)
    
    return db_path


class TestArchiveExport:
    """Test archive export functionality."""
    
    def test_export_to_tar_tsv(self, sample_database, temp_dir):
        """Test exporting database to tar archive with TSV format."""
        output_file = temp_dir / "test_export.tar"
        graph_name = "test_graph"
        
        with GraphDatabase(sample_database) as db:
            db.export_to_archive(
                output_path=output_file,
                graph_name=graph_name,
                format=KGXFormat.TSV,
                compress=False
            )
        
        # Verify tar file was created
        assert output_file.exists()
        
        # Verify tar contents
        with tarfile.open(output_file, "r") as tar:
            members = tar.getnames()
            expected_files = [f"{graph_name}_nodes.tsv", f"{graph_name}_edges.tsv"]
            assert set(members) == set(expected_files)
            
            # Extract and verify nodes file
            nodes_member = tar.extractfile(f"{graph_name}_nodes.tsv")
            nodes_content = nodes_member.read().decode('utf-8')
            assert "id\tcategory\tname\tprovided_by" in nodes_content
            assert "HGNC:123\tbiolink:Gene\tgene1\thgnc" in nodes_content
            assert "MONDO:001\tbiolink:Disease\tdisease1\tmondo" in nodes_content
            
            # Extract and verify edges file
            edges_member = tar.extractfile(f"{graph_name}_edges.tsv")
            edges_content = edges_member.read().decode('utf-8')
            assert "subject\tpredicate\tobject\tcategory\tprovided_by" in edges_content
            assert "HGNC:123\tbiolink:related_to\tMONDO:001" in edges_content
    
    def test_export_to_tar_gz_jsonl(self, sample_database, temp_dir):
        """Test exporting database to compressed tar.gz archive with JSONL format."""
        output_file = temp_dir / "test_export.tar.gz"
        graph_name = "test_graph"
        
        with GraphDatabase(sample_database) as db:
            db.export_to_archive(
                output_path=output_file,
                graph_name=graph_name,
                format=KGXFormat.JSONL,
                compress=True
            )
        
        # Verify tar.gz file was created
        assert output_file.exists()
        
        # Verify tar.gz contents
        with tarfile.open(output_file, "r:gz") as tar:
            members = tar.getnames()
            expected_files = [f"{graph_name}_nodes.jsonl", f"{graph_name}_edges.jsonl"]
            assert set(members) == set(expected_files)
            
            # Extract and verify nodes file
            nodes_member = tar.extractfile(f"{graph_name}_nodes.jsonl")
            nodes_content = nodes_member.read().decode('utf-8')
            lines = nodes_content.strip().split('\n')
            assert len(lines) == 3  # 3 nodes
            
            # Verify JSONL format
            import json
            for line in lines:
                node_data = json.loads(line)
                assert "id" in node_data
                assert "category" in node_data
    
    def test_export_to_tar_parquet(self, sample_database, temp_dir):
        """Test exporting database to tar archive with Parquet format."""
        output_file = temp_dir / "test_export.tar"
        graph_name = "test_graph"
        
        with GraphDatabase(sample_database) as db:
            db.export_to_archive(
                output_path=output_file,
                graph_name=graph_name,
                format=KGXFormat.PARQUET,
                compress=False
            )
        
        # Verify tar file was created
        assert output_file.exists()
        
        # Verify tar contents
        with tarfile.open(output_file, "r") as tar:
            members = tar.getnames()
            expected_files = [f"{graph_name}_nodes.parquet", f"{graph_name}_edges.parquet"]
            assert set(members) == set(expected_files)
    
    def test_export_to_archive_with_custom_graph_name(self, sample_database, temp_dir):
        """Test archive export with custom graph name."""
        output_file = temp_dir / "custom_export.tar"
        graph_name = "monarch_kg_v2024"
        
        with GraphDatabase(sample_database) as db:
            db.export_to_archive(
                output_path=output_file,
                graph_name=graph_name,
                format=KGXFormat.TSV,
                compress=False
            )
        
        # Verify tar contents have custom graph name
        with tarfile.open(output_file, "r") as tar:
            members = tar.getnames()
            expected_files = [f"{graph_name}_nodes.tsv", f"{graph_name}_edges.tsv"]
            assert set(members) == set(expected_files)


class TestArchiveExportEdgeCases:
    """Test edge cases and error conditions for archive export."""
    
    def test_export_empty_database_to_archive(self, temp_dir):
        """Test exporting empty database to archive."""
        db_path = temp_dir / "empty.duckdb"
        output_file = temp_dir / "empty_export.tar"
        
        with GraphDatabase(db_path) as db:
            # Create empty tables
            db.conn.execute("CREATE TABLE nodes (id VARCHAR)")
            db.conn.execute("CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR)")
            
            db.export_to_archive(
                output_path=output_file,
                graph_name="empty_graph",
                format=KGXFormat.TSV,
                compress=False
            )
        
        # Verify tar file was created with empty files
        assert output_file.exists()
        
        with tarfile.open(output_file, "r") as tar:
            members = tar.getnames()
            assert "empty_graph_nodes.tsv" in members
            assert "empty_graph_edges.tsv" in members
            
            # Verify empty nodes file has header
            nodes_member = tar.extractfile("empty_graph_nodes.tsv")
            nodes_content = nodes_member.read().decode('utf-8')
            assert "id" in nodes_content  # Header should be present
    
    def test_export_to_archive_with_special_characters_in_graph_name(self, sample_database, temp_dir):
        """Test archive export with special characters in graph name."""
        output_file = temp_dir / "special_export.tar"
        graph_name = "monarch-kg_v2024.1"
        
        with GraphDatabase(sample_database) as db:
            db.export_to_archive(
                output_path=output_file,
                graph_name=graph_name,
                format=KGXFormat.TSV,
                compress=False
            )
        
        # Verify files are created with special characters preserved
        with tarfile.open(output_file, "r") as tar:
            members = tar.getnames()
            expected_files = [f"{graph_name}_nodes.tsv", f"{graph_name}_edges.tsv"]
            assert set(members) == set(expected_files)
    
    def test_export_to_archive_creates_parent_directories(self, sample_database, temp_dir):
        """Test that archive export creates parent directories if they don't exist."""
        nested_path = temp_dir / "nested" / "dir" / "export.tar"
        
        with GraphDatabase(sample_database) as db:
            db.export_to_archive(
                output_path=nested_path,
                graph_name="test_graph",
                format=KGXFormat.TSV,
                compress=False
            )
        
        # Verify nested directories were created
        assert nested_path.exists()
        assert nested_path.parent.exists()


class TestLooseFileExport:
    """Test loose file export (non-archive) functionality for comparison."""
    
    def test_export_to_loose_files_tsv(self, sample_database, temp_dir):
        """Test exporting database to loose TSV files."""
        graph_name = "test_graph"
        
        with GraphDatabase(sample_database) as db:
            db.export_to_loose_files(
                output_directory=temp_dir,
                graph_name=graph_name,
                format=KGXFormat.TSV
            )
        
        # Verify loose files were created
        nodes_file = temp_dir / f"{graph_name}_nodes.tsv"
        edges_file = temp_dir / f"{graph_name}_edges.tsv"
        
        assert nodes_file.exists()
        assert edges_file.exists()
        
        # Verify content
        nodes_content = nodes_file.read_text()
        assert "id\tcategory\tname\tprovided_by" in nodes_content
        assert "HGNC:123\tbiolink:Gene\tgene1\thgnc" in nodes_content
    
    def test_export_to_loose_files_jsonl(self, sample_database, temp_dir):
        """Test exporting database to loose JSONL files."""
        graph_name = "test_graph"
        
        with GraphDatabase(sample_database) as db:
            db.export_to_loose_files(
                output_directory=temp_dir,
                graph_name=graph_name,
                format=KGXFormat.JSONL
            )
        
        # Verify loose files were created
        nodes_file = temp_dir / f"{graph_name}_nodes.jsonl"
        edges_file = temp_dir / f"{graph_name}_edges.jsonl"
        
        assert nodes_file.exists()
        assert edges_file.exists()
        
        # Verify JSONL content
        nodes_content = nodes_file.read_text()
        lines = nodes_content.strip().split('\n')
        assert len(lines) == 3  # 3 nodes
        
        import json
        for line in lines:
            node_data = json.loads(line)
            assert "id" in node_data


class TestExportFormatDetection:
    """Test export format detection and file extension mapping."""
    
    def test_format_to_extension_mapping(self):
        """Test that format enum maps to correct file extensions."""
        from koza.graph_operations.utils import _get_file_extension
        
        assert _get_file_extension(KGXFormat.TSV) == ".tsv"
        assert _get_file_extension(KGXFormat.JSONL) == ".jsonl"
        assert _get_file_extension(KGXFormat.PARQUET) == ".parquet"
    
    def test_archive_filename_generation(self):
        """Test archive filename generation with different formats."""
        from koza.graph_operations.utils import _generate_archive_filenames
        
        nodes_name, edges_name = _generate_archive_filenames("test_graph", KGXFormat.TSV)
        assert nodes_name == "test_graph_nodes.tsv"
        assert edges_name == "test_graph_edges.tsv"
        
        nodes_name, edges_name = _generate_archive_filenames("monarch_kg", KGXFormat.JSONL)
        assert nodes_name == "monarch_kg_nodes.jsonl"
        assert edges_name == "monarch_kg_edges.jsonl"


class TestIntegrationWithExistingFunctionality:
    """Test integration with existing export functionality."""
    
    def test_backward_compatibility_with_existing_export(self, sample_database, temp_dir):
        """Test that existing export_to_format still works."""
        output_file = temp_dir / "test_export.tsv"
        
        with GraphDatabase(sample_database) as db:
            # This should still work as before
            db.export_to_format("nodes", output_file, KGXFormat.TSV)
        
        assert output_file.exists()
        content = output_file.read_text()
        assert "id\tcategory\tname\tprovided_by" in content
    
    def test_archive_export_uses_existing_export_internally(self, sample_database, temp_dir):
        """Test that archive export uses existing export_to_format internally."""
        output_file = temp_dir / "test_export.tar"
        
        def mock_export_side_effect(table_name, output_path, format_type):
            """Mock that creates actual temp files for the archive to use."""
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # Create a simple test file
            if table_name == "nodes":
                output_path.write_text("id\tcategory\tname\nHGNC:123\tbiolink:Gene\tgene1\n")
            elif table_name == "edges":
                output_path.write_text("subject\tpredicate\tobject\nHGNC:123\tbiolink:related_to\tMONDO:001\n")
        
        with patch.object(GraphDatabase, 'export_to_format', side_effect=mock_export_side_effect) as mock_export:
            with GraphDatabase(sample_database) as db:
                db.export_to_archive(
                    output_path=output_file,
                    graph_name="test_graph",
                    format=KGXFormat.TSV,
                    compress=False
                )
            
            # Should have called export_to_format twice (nodes and edges)
            assert mock_export.call_count == 2
            
            # Verify the calls were made with correct table names
            call_args = [call[0] for call in mock_export.call_args_list]
            table_names = [args[0] for args in call_args]
            assert "nodes" in table_names
            assert "edges" in table_names
            
        # Verify the archive was actually created
        assert output_file.exists()


if __name__ == "__main__":
    pytest.main([__file__])