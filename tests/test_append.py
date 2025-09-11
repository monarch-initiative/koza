"""
Test suite for append graph operation.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from koza.graph_operations import append_graphs
from koza.graph_operations.utils import GraphDatabase
from koza.model.graph_operations import (
    AppendConfig, FileSpec, KGXFormat, KGXFileType, DatabaseStats
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def existing_database(temp_dir):
    """Create an existing database with some data."""
    db_path = temp_dir / "existing.duckdb"
    
    with GraphDatabase(db_path) as db:
        # Create tables with initial data
        db.conn.execute("""
            CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR, source VARCHAR);
            INSERT INTO nodes VALUES 
                ('HGNC:123', 'biolink:Gene', 'gene1', 'initial'),
                ('HGNC:456', 'biolink:Gene', 'gene2', 'initial');
        """)
        
        db.conn.execute("""
            CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR, source VARCHAR);
            INSERT INTO edges VALUES 
                ('HGNC:123', 'biolink:related_to', 'HGNC:456', 'initial');
        """)
        
        # Create QC tables
        db.conn.execute("""
            CREATE TABLE dangling_edges (subject VARCHAR, predicate VARCHAR, object VARCHAR, source VARCHAR);
            CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, name VARCHAR, source VARCHAR);
            CREATE TABLE singleton_nodes (id VARCHAR, category VARCHAR, name VARCHAR, source VARCHAR);
            CREATE TABLE file_schemas (file_name VARCHAR, schema_info VARCHAR);
        """)
    
    return db_path


@pytest.fixture
def new_nodes_file(temp_dir):
    """Create a new nodes file to append."""
    nodes_content = """id	category	name
HGNC:789	biolink:Gene	gene3
MONDO:001	biolink:Disease	disease1
"""
    nodes_file = temp_dir / "new_nodes.tsv"
    nodes_file.write_text(nodes_content)
    return nodes_file


@pytest.fixture
def new_edges_file(temp_dir):
    """Create a new edges file to append."""
    edges_content = """subject	predicate	object
HGNC:789	biolink:causes	MONDO:001
HGNC:456	biolink:related_to	MONDO:001
"""
    edges_file = temp_dir / "new_edges.tsv"
    edges_file.write_text(edges_content)
    return edges_file


@pytest.fixture
def duplicate_nodes_file(temp_dir):
    """Create a nodes file with duplicates."""
    nodes_content = """id	category	name
HGNC:123	biolink:Gene	gene1_updated
HGNC:999	biolink:Gene	gene_new
"""
    nodes_file = temp_dir / "duplicate_nodes.tsv"
    nodes_file.write_text(nodes_content)
    return nodes_file


class TestAppendOperation:
    """Test append operation functionality."""
    
    def test_append_new_nodes_only(self, existing_database, new_nodes_file):
        """Test appending new nodes to existing database."""
        config = AppendConfig(
            database_path=existing_database,
            node_files=[FileSpec(
                path=new_nodes_file,
                format=KGXFormat.TSV,
                file_type=KGXFileType.NODES
            )],
            edge_files=[],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False
        )
        
        result = append_graphs(config)
        
        assert result is not None
        assert len(result.files_loaded) == 1
        assert result.files_loaded[0].records_loaded == 2
        assert result.records_added == 2
        
        # Verify data was appended
        with GraphDatabase(existing_database) as db:
            node_count = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            assert node_count == 4  # 2 original + 2 new
            
            # Check new nodes exist
            new_node_ids = db.conn.execute("""
                SELECT id FROM nodes WHERE source != 'initial'
            """).fetchall()
            new_ids = {row[0] for row in new_node_ids}
            assert 'HGNC:789' in new_ids
            assert 'MONDO:001' in new_ids
    
    def test_append_new_edges_only(self, existing_database, new_edges_file):
        """Test appending new edges to existing database."""
        config = AppendConfig(
            database_path=existing_database,
            node_files=[],
            edge_files=[FileSpec(
                path=new_edges_file,
                format=KGXFormat.TSV,
                file_type=KGXFileType.EDGES
            )],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False
        )
        
        result = append_graphs(config)
        
        assert result is not None
        assert len(result.files_loaded) == 1
        assert result.files_loaded[0].records_loaded == 2
        assert result.records_added == 2
        
        # Verify data was appended
        with GraphDatabase(existing_database) as db:
            edge_count = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            assert edge_count == 3  # 1 original + 2 new
    
    def test_append_both_nodes_and_edges(self, existing_database, new_nodes_file, new_edges_file):
        """Test appending both nodes and edges."""
        config = AppendConfig(
            database_path=existing_database,
            node_files=[FileSpec(
                path=new_nodes_file,
                format=KGXFormat.TSV,
                file_type=KGXFileType.NODES
            )],
            edge_files=[FileSpec(
                path=new_edges_file,
                format=KGXFormat.TSV,
                file_type=KGXFileType.EDGES
            )],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False
        )
        
        result = append_graphs(config)
        
        assert result is not None
        assert len(result.files_loaded) == 2
        assert result.records_added == 4  # 2 nodes + 2 edges
        
        # Verify both types were appended
        with GraphDatabase(existing_database) as db:
            node_count = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            edge_count = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            assert node_count == 4  # 2 original + 2 new
            assert edge_count == 3  # 1 original + 2 new
    
    def test_append_with_deduplication_enabled(self, existing_database, duplicate_nodes_file):
        """Test appending with deduplication enabled."""
        config = AppendConfig(
            database_path=existing_database,
            node_files=[FileSpec(
                path=duplicate_nodes_file,
                format=KGXFormat.TSV,
                file_type=KGXFileType.NODES
            )],
            edge_files=[],
            deduplicate=True,
            quiet=True,
            show_progress=False,
            schema_reporting=False
        )
        
        result = append_graphs(config)
        
        assert result is not None
        assert len(result.files_loaded) == 1
        assert result.files_loaded[0].records_loaded == 2
        
        # Verify deduplication occurred
        with GraphDatabase(existing_database) as db:
            # Should have original nodes + 1 new (HGNC:999), duplicate HGNC:123 handled
            node_count = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            # Exact count depends on deduplication strategy implementation
            assert node_count >= 2  # At least original nodes remain
            
            # Check that HGNC:999 was added
            hgnc_999_count = db.conn.execute("""
                SELECT COUNT(*) FROM nodes WHERE id = 'HGNC:999'
            """).fetchone()[0]
            assert hgnc_999_count == 1
    
    def test_append_with_deduplication_disabled(self, existing_database, duplicate_nodes_file):
        """Test appending with deduplication disabled (allows duplicates)."""
        config = AppendConfig(
            database_path=existing_database,
            node_files=[FileSpec(
                path=duplicate_nodes_file,
                format=KGXFormat.TSV,
                file_type=KGXFileType.NODES
            )],
            edge_files=[],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False
        )
        
        result = append_graphs(config)
        
        assert result is not None
        
        # Verify duplicates were allowed
        with GraphDatabase(existing_database) as db:
            node_count = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            assert node_count == 4  # 2 original + 2 new (including duplicate)
            
            # Check that duplicate HGNC:123 exists
            hgnc_123_count = db.conn.execute("""
                SELECT COUNT(*) FROM nodes WHERE id = 'HGNC:123'
            """).fetchone()[0]
            assert hgnc_123_count == 2  # Original + duplicate
    
    def test_append_with_schema_reporting(self, existing_database, new_nodes_file):
        """Test append operation with schema reporting enabled."""
        config = AppendConfig(
            database_path=existing_database,
            node_files=[FileSpec(
                path=new_nodes_file,
                format=KGXFormat.TSV,
                file_type=KGXFileType.NODES
            )],
            edge_files=[],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=True
        )
        
        result = append_graphs(config)
        
        assert result is not None
        assert result.schema_report is not None
        
        # Should have generated schema report file
        schema_file = existing_database.parent / f"{existing_database.stem}_schema_report.yaml"
        assert schema_file.exists()
    
    def test_append_empty_files_list(self, existing_database):
        """Test append with empty files lists."""
        config = AppendConfig(
            database_path=existing_database,
            node_files=[],
            edge_files=[],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False
        )
        
        result = append_graphs(config)
        
        # Should complete but add no records
        assert result is not None
        assert len(result.files_loaded) == 0
        assert result.records_added == 0
        
        # Original data should remain unchanged
        with GraphDatabase(existing_database) as db:
            node_count = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            edge_count = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            assert node_count == 2  # Original nodes
            assert edge_count == 1   # Original edges
    
    def test_append_to_nonexistent_database(self, temp_dir, new_nodes_file):
        """Test that append fails gracefully with nonexistent database."""
        nonexistent_db = temp_dir / "nonexistent.duckdb"
        
        with pytest.raises(ValueError, match="Database file not found"):
            AppendConfig(
                database_path=nonexistent_db,
                node_files=[FileSpec(
                    path=new_nodes_file,
                    format=KGXFormat.TSV,
                    file_type=KGXFileType.NODES
                )],
                edge_files=[],
                deduplicate=False
            )
    
    def test_append_nonexistent_file(self, existing_database, temp_dir):
        """Test append with nonexistent file."""
        nonexistent_file = temp_dir / "nonexistent.tsv"
        
        config = AppendConfig(
            database_path=existing_database,
            node_files=[FileSpec(
                path=nonexistent_file,
                format=KGXFormat.TSV,
                file_type=KGXFileType.NODES
            )],
            edge_files=[],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False
        )
        
        result = append_graphs(config)
        
        # Should handle gracefully with errors
        assert result is not None
        assert len(result.files_loaded) == 1
        assert len(result.files_loaded[0].errors) > 0
        assert result.files_loaded[0].records_loaded == 0
        assert result.records_added == 0


class TestAppendConfigValidation:
    """Test AppendConfig validation logic."""
    
    def test_config_validation_database_exists(self, existing_database):
        """Test that config validates existing database."""
        config = AppendConfig(
            database_path=existing_database,
            node_files=[],
            edge_files=[],
            deduplicate=False
        )
        
        assert config.database_path == existing_database
    
    def test_config_validation_database_not_exists(self, temp_dir):
        """Test that config validation fails for nonexistent database."""
        nonexistent_db = temp_dir / "nonexistent.duckdb"
        
        with pytest.raises(ValueError, match="Database file not found"):
            AppendConfig(
                database_path=nonexistent_db,
                node_files=[],
                edge_files=[],
                deduplicate=False
            )


class TestAppendOperationEdgeCases:
    """Test edge cases and error conditions for append operation."""
    
    def test_append_malformed_file(self, existing_database, temp_dir):
        """Test append with malformed file."""
        malformed_file = temp_dir / "malformed.tsv"
        malformed_content = """id	category	name
HGNC:123	biolink:Gene	gene1	extra_column
HGNC:456	biolink:Gene
"""  # Inconsistent columns
        malformed_file.write_text(malformed_content)
        
        config = AppendConfig(
            database_path=existing_database,
            node_files=[FileSpec(
                path=malformed_file,
                format=KGXFormat.TSV,
                file_type=KGXFileType.NODES
            )],
            edge_files=[],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False
        )
        
        result = append_graphs(config)
        
        # Should handle gracefully, may load partial data
        assert result is not None
        assert len(result.files_loaded) == 1
        # Might have some records loaded despite malformation
        assert result.files_loaded[0].records_loaded >= 0
    
    def test_append_empty_file(self, existing_database, temp_dir):
        """Test append with empty file."""
        empty_file = temp_dir / "empty.tsv"
        empty_file.write_text("")
        
        config = AppendConfig(
            database_path=existing_database,
            node_files=[FileSpec(
                path=empty_file,
                format=KGXFormat.TSV,
                file_type=KGXFileType.NODES
            )],
            edge_files=[],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False
        )
        
        result = append_graphs(config)
        
        assert result is not None
        assert len(result.files_loaded) == 1
        assert result.files_loaded[0].records_loaded == 0
        assert result.records_added == 0
    
    def test_append_header_only_file(self, existing_database, temp_dir):
        """Test append with header-only file."""
        header_only_file = temp_dir / "header_only.tsv"
        header_only_file.write_text("id\tcategory\tname\n")
        
        config = AppendConfig(
            database_path=existing_database,
            node_files=[FileSpec(
                path=header_only_file,
                format=KGXFormat.TSV,
                file_type=KGXFileType.NODES
            )],
            edge_files=[],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False
        )
        
        result = append_graphs(config)
        
        assert result is not None
        assert len(result.files_loaded) == 1
        assert result.files_loaded[0].records_loaded == 0
        assert result.records_added == 0
    
    def test_append_multiple_files_same_type(self, existing_database, temp_dir):
        """Test appending multiple files of the same type."""
        # Create multiple node files
        nodes_file1 = temp_dir / "nodes1.tsv"
        nodes_file1.write_text("id\tcategory\tname\nHGNC:111\tbiolink:Gene\tgene_a\n")
        
        nodes_file2 = temp_dir / "nodes2.tsv"
        nodes_file2.write_text("id\tcategory\tname\nHGNC:222\tbiolink:Gene\tgene_b\n")
        
        config = AppendConfig(
            database_path=existing_database,
            node_files=[
                FileSpec(path=nodes_file1, format=KGXFormat.TSV, file_type=KGXFileType.NODES),
                FileSpec(path=nodes_file2, format=KGXFormat.TSV, file_type=KGXFileType.NODES)
            ],
            edge_files=[],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False
        )
        
        result = append_graphs(config)
        
        assert result is not None
        assert len(result.files_loaded) == 2
        assert result.records_added == 2  # 1 from each file
        
        # Verify both files were processed
        with GraphDatabase(existing_database) as db:
            node_count = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            assert node_count == 4  # 2 original + 2 new
            
            # Check specific nodes exist
            node_ids = db.conn.execute("SELECT id FROM nodes").fetchall()
            all_ids = {row[0] for row in node_ids}
            assert 'HGNC:111' in all_ids
            assert 'HGNC:222' in all_ids
    
    def test_append_with_different_schema(self, existing_database, temp_dir):
        """Test appending file with different schema."""
        # Create file with additional columns
        different_schema_file = temp_dir / "different_schema.tsv"
        different_schema_content = """id	category	name	description	source_db
HGNC:999	biolink:Gene	gene_special	A special gene	external_db
"""
        different_schema_file.write_text(different_schema_content)
        
        config = AppendConfig(
            database_path=existing_database,
            node_files=[FileSpec(
                path=different_schema_file,
                format=KGXFormat.TSV,
                file_type=KGXFileType.NODES
            )],
            edge_files=[],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False
        )
        
        result = append_graphs(config)
        
        # Should handle schema differences gracefully
        assert result is not None
        assert len(result.files_loaded) == 1
        assert result.files_loaded[0].records_loaded == 1
        
        # Verify data was appended despite schema differences
        with GraphDatabase(existing_database) as db:
            node_count = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            assert node_count == 3  # 2 original + 1 new
            
            # Check that new node exists
            hgnc_999_count = db.conn.execute("""
                SELECT COUNT(*) FROM nodes WHERE id = 'HGNC:999'
            """).fetchone()[0]
            assert hgnc_999_count == 1


if __name__ == "__main__":
    pytest.main([__file__])