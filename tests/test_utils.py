"""
Test suite for graph operations utils module.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import duckdb

from koza.graph_operations.utils import (
    GraphDatabase, print_operation_summary, _analyze_file_schema, 
    _setup_database, create_final_tables
)
from koza.model.graph_operations import (
    DatabaseStats, OperationSummary, FileSpec, KGXFormat, KGXFileType, FileLoadResult
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_tsv_file(temp_dir):
    """Create a sample TSV file."""
    content = """id	category	name	description
HGNC:123	biolink:Gene	gene1	A test gene
HGNC:456	biolink:Gene	gene2	Another gene
"""
    file_path = temp_dir / "sample.tsv"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def sample_jsonl_file(temp_dir):
    """Create a sample JSONL file."""
    content = """{"id": "CHEBI:123", "category": "biolink:ChemicalEntity", "name": "chemical1"}
{"id": "CHEBI:456", "category": "biolink:ChemicalEntity", "name": "chemical2"}
"""
    file_path = temp_dir / "sample.jsonl"
    file_path.write_text(content)
    return file_path


class TestGraphDatabase:
    """Test GraphDatabase context manager and operations."""
    
    def test_graph_database_in_memory(self):
        """Test GraphDatabase with in-memory database."""
        with GraphDatabase(None) as db:
            assert db.conn is not None
            assert isinstance(db.conn, duckdb.DuckDBPyConnection)
            
            # Test basic operation
            result = db.conn.execute("SELECT 1 as test").fetchone()
            assert result[0] == 1
    
    def test_graph_database_file_based(self, temp_dir):
        """Test GraphDatabase with file-based database."""
        db_path = temp_dir / "test.duckdb"
        
        with GraphDatabase(db_path) as db:
            assert db.conn is not None
            
            # Create a test table
            db.conn.execute("CREATE TABLE test (id INTEGER, name VARCHAR)")
            db.conn.execute("INSERT INTO test VALUES (1, 'test')")
        
        # Verify persistence
        assert db_path.exists()
        
        # Reconnect and verify data persists
        with GraphDatabase(db_path) as db:
            result = db.conn.execute("SELECT * FROM test").fetchone()
            assert result == (1, 'test')
    
    def test_graph_database_get_stats_empty(self, temp_dir):
        """Test get_stats with empty database."""
        db_path = temp_dir / "test.duckdb"
        
        with GraphDatabase(db_path) as db:
            stats = db.get_stats()
            
            assert isinstance(stats, DatabaseStats)
            assert stats.nodes == 0
            assert stats.edges == 0
            assert stats.dangling_edges == 0
            assert stats.duplicate_nodes == 0
            assert stats.singleton_nodes == 0
            assert stats.database_size_mb is not None
            assert stats.database_size_mb >= 0
    
    def test_graph_database_get_stats_with_data(self, temp_dir):
        """Test get_stats with actual data."""
        db_path = temp_dir / "test.duckdb"
        
        with GraphDatabase(db_path) as db:
            # Create tables with data
            db.conn.execute("""
                CREATE TABLE nodes (id VARCHAR, category VARCHAR);
                INSERT INTO nodes VALUES ('HGNC:123', 'biolink:Gene'), ('HGNC:456', 'biolink:Gene');
            """)
            
            db.conn.execute("""
                CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR);
                INSERT INTO edges VALUES ('HGNC:123', 'biolink:related_to', 'HGNC:456');
            """)
            
            db.conn.execute("""
                CREATE TABLE dangling_edges (subject VARCHAR, predicate VARCHAR, object VARCHAR);
                INSERT INTO dangling_edges VALUES ('HGNC:999', 'biolink:related_to', 'HGNC:888');
            """)
            
            stats = db.get_stats()
            
            assert stats.nodes == 2
            assert stats.edges == 1
            assert stats.dangling_edges == 1
            assert stats.duplicate_nodes == 0
            assert stats.singleton_nodes == 0
    
    def test_graph_database_load_file_tsv(self, temp_dir, sample_tsv_file):
        """Test loading TSV file."""
        db_path = temp_dir / "test.duckdb"
        
        file_spec = FileSpec(
            path=sample_tsv_file,
            format=KGXFormat.TSV,
            file_type=KGXFileType.NODES,
            source_name="test"
        )
        
        with GraphDatabase(db_path) as db:
            result = db.load_file(file_spec)
            
            assert isinstance(result, FileLoadResult)
            assert result.records_loaded == 2
            assert result.detected_format == KGXFormat.TSV
            assert len(result.errors) == 0
            assert result.temp_table_name is not None
            
            # Verify data was loaded
            count = db.conn.execute(f"SELECT COUNT(*) FROM {result.temp_table_name}").fetchone()[0]
            assert count == 2
    
    def test_graph_database_load_file_jsonl(self, temp_dir, sample_jsonl_file):
        """Test loading JSONL file."""
        db_path = temp_dir / "test.duckdb"
        
        file_spec = FileSpec(
            path=sample_jsonl_file,
            format=KGXFormat.JSONL,
            file_type=KGXFileType.NODES,
            source_name="test"
        )
        
        with GraphDatabase(db_path) as db:
            result = db.load_file(file_spec)
            
            assert isinstance(result, FileLoadResult)
            assert result.records_loaded == 2
            assert result.detected_format == KGXFormat.JSONL
            assert len(result.errors) == 0
    
    def test_graph_database_load_nonexistent_file(self, temp_dir):
        """Test loading nonexistent file."""
        db_path = temp_dir / "test.duckdb"
        nonexistent_file = temp_dir / "nonexistent.tsv"
        
        file_spec = FileSpec(
            path=nonexistent_file,
            format=KGXFormat.TSV,
            file_type=KGXFileType.NODES,
            source_name="test"
        )
        
        with GraphDatabase(db_path) as db:
            result = db.load_file(file_spec)
            
            assert isinstance(result, FileLoadResult)
            assert result.records_loaded == 0
            assert len(result.errors) > 0
            assert "not found" in result.errors[0].lower()
    
    def test_graph_database_export_to_format_tsv(self, temp_dir):
        """Test exporting table to TSV format."""
        db_path = temp_dir / "test.duckdb"
        output_file = temp_dir / "export.tsv"
        
        with GraphDatabase(db_path) as db:
            # Create test table
            db.conn.execute("""
                CREATE TABLE test_table (id VARCHAR, name VARCHAR);
                INSERT INTO test_table VALUES ('1', 'test1'), ('2', 'test2');
            """)
            
            db.export_to_format("test_table", output_file, KGXFormat.TSV)
            
            assert output_file.exists()
            content = output_file.read_text()
            assert "id\tname" in content
            assert "1\ttest1" in content
            assert "2\ttest2" in content
    
    def test_graph_database_export_to_format_jsonl(self, temp_dir):
        """Test exporting table to JSONL format."""
        db_path = temp_dir / "test.duckdb"
        output_file = temp_dir / "export.jsonl"
        
        with GraphDatabase(db_path) as db:
            # Create test table
            db.conn.execute("""
                CREATE TABLE test_table (id VARCHAR, name VARCHAR);
                INSERT INTO test_table VALUES ('1', 'test1'), ('2', 'test2');
            """)
            
            db.export_to_format("test_table", output_file, KGXFormat.JSONL)
            
            assert output_file.exists()
            content = output_file.read_text()
            assert '{"id":"1","name":"test1"}' in content
            assert '{"id":"2","name":"test2"}' in content
    
    def test_graph_database_export_nonexistent_table(self, temp_dir):
        """Test exporting nonexistent table."""
        db_path = temp_dir / "test.duckdb"
        output_file = temp_dir / "export.tsv"
        
        with GraphDatabase(db_path) as db:
            with pytest.raises(Exception):
                db.export_to_format("nonexistent_table", output_file, KGXFormat.TSV)


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_analyze_file_schema_tsv(self, sample_tsv_file):
        """Test analyzing TSV file schema."""
        schema = _analyze_file_schema(sample_tsv_file, KGXFormat.TSV)
        
        assert isinstance(schema, dict)
        assert "columns" in schema
        assert "sample_data" in schema
        assert schema["columns"] == 4
        assert len(schema["sample_data"]) > 0
    
    def test_analyze_file_schema_jsonl(self, sample_jsonl_file):
        """Test analyzing JSONL file schema."""
        schema = _analyze_file_schema(sample_jsonl_file, KGXFormat.JSONL)
        
        assert isinstance(schema, dict)
        assert "columns" in schema
        assert "sample_data" in schema
        assert schema["columns"] >= 3  # id, category, name
    
    def test_analyze_file_schema_nonexistent(self, temp_dir):
        """Test analyzing nonexistent file."""
        nonexistent_file = temp_dir / "nonexistent.tsv"
        
        schema = _analyze_file_schema(nonexistent_file, KGXFormat.TSV)
        
        assert schema == {"columns": 0, "sample_data": []}
    
    def test_setup_database(self, temp_dir):
        """Test database setup."""
        db_path = temp_dir / "test.duckdb"
        
        with GraphDatabase(db_path) as db:
            _setup_database(db.conn)
            
            # Check that QC tables are created
            tables = db.conn.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name IN ('dangling_edges', 'duplicate_nodes', 'singleton_nodes', 'file_schemas')
            """).fetchall()
            
            table_names = {row[0] for row in tables}
            expected_tables = {'dangling_edges', 'duplicate_nodes', 'singleton_nodes', 'file_schemas'}
            assert expected_tables.issubset(table_names)
    
    def test_print_operation_summary_success(self, capsys):
        """Test printing successful operation summary."""
        summary = OperationSummary(
            operation="test",
            success=True,
            message="Test completed successfully",
            stats=DatabaseStats(nodes=100, edges=50),
            files_processed=2,
            total_time_seconds=1.5,
            warnings=[],
            errors=[]
        )
        
        print_operation_summary(summary)
        
        captured = capsys.readouterr()
        assert "✓ test completed successfully" in captured.out
        assert "Test completed successfully" in captured.out
        assert "Nodes: 100" in captured.out
        assert "Edges: 50" in captured.out
        assert "Files processed: 2" in captured.out
        assert "1.50s" in captured.out
    
    def test_print_operation_summary_failure(self, capsys):
        """Test printing failed operation summary."""
        summary = OperationSummary(
            operation="test",
            success=False,
            message="Test failed",
            stats=None,
            files_processed=1,
            total_time_seconds=0.5,
            warnings=["Warning message"],
            errors=["Error message"]
        )
        
        print_operation_summary(summary)
        
        captured = capsys.readouterr()
        assert "✗ test failed" in captured.out
        assert "Test failed" in captured.out
        assert "Files processed: 1" in captured.out
        assert "⚠️  Warnings:" in captured.out
        assert "Warning message" in captured.out
        assert "❌ Errors:" in captured.out
        assert "Error message" in captured.out
    
    def test_print_operation_summary_with_warnings_only(self, capsys):
        """Test printing operation summary with warnings but no errors."""
        summary = OperationSummary(
            operation="test",
            success=True,
            message="Test completed with warnings",
            stats=DatabaseStats(nodes=10, edges=5),
            files_processed=1,
            total_time_seconds=0.3,
            warnings=["Some warning"],
            errors=[]
        )
        
        print_operation_summary(summary)
        
        captured = capsys.readouterr()
        assert "✓ test completed successfully" in captured.out
        assert "⚠️  Warnings:" in captured.out
        assert "Some warning" in captured.out
        assert "❌ Errors:" not in captured.out


class TestCreateFinalTables:
    """Test create_final_tables function."""
    
    def test_create_final_tables_nodes_only(self, temp_dir):
        """Test creating final tables with nodes only."""
        db_path = temp_dir / "test.duckdb"
        
        # Mock file load results
        node_result = FileLoadResult(
            file_spec=FileSpec(path=Path("test.tsv"), format=KGXFormat.TSV, file_type=KGXFileType.NODES),
            records_loaded=2,
            detected_format=KGXFormat.TSV,
            load_time_seconds=0.1,
            temp_table_name="temp_nodes_test"
        )
        
        with GraphDatabase(db_path) as db:
            # Create temp table
            db.conn.execute("""
                CREATE TABLE temp_nodes_test (id VARCHAR, category VARCHAR, name VARCHAR, source VARCHAR);
                INSERT INTO temp_nodes_test VALUES 
                    ('HGNC:123', 'biolink:Gene', 'gene1', 'test'),
                    ('HGNC:456', 'biolink:Gene', 'gene2', 'test');
            """)
            
            create_final_tables(db, [node_result], [])
            
            # Check nodes table was created
            nodes_count = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            assert nodes_count == 2
            
            # Check temp table was cleaned up
            with pytest.raises(Exception):
                db.conn.execute("SELECT * FROM temp_nodes_test")
    
    def test_create_final_tables_edges_only(self, temp_dir):
        """Test creating final tables with edges only."""
        db_path = temp_dir / "test.duckdb"
        
        # Mock file load results
        edge_result = FileLoadResult(
            file_spec=FileSpec(path=Path("test.tsv"), format=KGXFormat.TSV, file_type=KGXFileType.EDGES),
            records_loaded=1,
            detected_format=KGXFormat.TSV,
            load_time_seconds=0.1,
            temp_table_name="temp_edges_test"
        )
        
        with GraphDatabase(db_path) as db:
            # Create temp table
            db.conn.execute("""
                CREATE TABLE temp_edges_test (subject VARCHAR, predicate VARCHAR, object VARCHAR, source VARCHAR);
                INSERT INTO temp_edges_test VALUES ('HGNC:123', 'biolink:related_to', 'HGNC:456', 'test');
            """)
            
            create_final_tables(db, [], [edge_result])
            
            # Check edges table was created
            edges_count = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            assert edges_count == 1
    
    def test_create_final_tables_both_nodes_and_edges(self, temp_dir):
        """Test creating final tables with both nodes and edges."""
        db_path = temp_dir / "test.duckdb"
        
        # Mock file load results
        node_result = FileLoadResult(
            file_spec=FileSpec(path=Path("nodes.tsv"), format=KGXFormat.TSV, file_type=KGXFileType.NODES),
            records_loaded=2,
            detected_format=KGXFormat.TSV,
            load_time_seconds=0.1,
            temp_table_name="temp_nodes_test"
        )
        
        edge_result = FileLoadResult(
            file_spec=FileSpec(path=Path("edges.tsv"), format=KGXFormat.TSV, file_type=KGXFileType.EDGES),
            records_loaded=1,
            detected_format=KGXFormat.TSV,
            load_time_seconds=0.1,
            temp_table_name="temp_edges_test"
        )
        
        with GraphDatabase(db_path) as db:
            # Create temp tables
            db.conn.execute("""
                CREATE TABLE temp_nodes_test (id VARCHAR, category VARCHAR, source VARCHAR);
                INSERT INTO temp_nodes_test VALUES 
                    ('HGNC:123', 'biolink:Gene', 'nodes'),
                    ('HGNC:456', 'biolink:Gene', 'nodes');
            """)
            
            db.conn.execute("""
                CREATE TABLE temp_edges_test (subject VARCHAR, predicate VARCHAR, object VARCHAR, source VARCHAR);
                INSERT INTO temp_edges_test VALUES ('HGNC:123', 'biolink:related_to', 'HGNC:456', 'edges');
            """)
            
            create_final_tables(db, [node_result], [edge_result])
            
            # Check both tables were created
            nodes_count = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            edges_count = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            
            assert nodes_count == 2
            assert edges_count == 1


if __name__ == "__main__":
    pytest.main([__file__])