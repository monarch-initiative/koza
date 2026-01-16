"""
Test suite for prune graph operation.
"""

import tempfile
from pathlib import Path

import pytest

from koza.graph_operations import prune_graph
from koza.graph_operations.utils import GraphDatabase
from koza.model.graph_operations import PruneConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def database_with_clean_graph(temp_dir):
    """Create a database with a clean graph (no dangling edges or singletons)."""
    db_path = temp_dir / "clean.duckdb"

    with GraphDatabase(db_path) as db:
        # Create nodes
        db.conn.execute("""
            CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR);
            INSERT INTO nodes VALUES 
                ('HGNC:123', 'biolink:Gene', 'gene1'),
                ('HGNC:456', 'biolink:Gene', 'gene2'),
                ('MONDO:001', 'biolink:Disease', 'disease1');
        """)

        # Create edges with all valid references
        db.conn.execute("""
            CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR);
            INSERT INTO edges VALUES 
                ('HGNC:123', 'biolink:related_to', 'MONDO:001'),
                ('HGNC:456', 'biolink:causes', 'MONDO:001');
        """)

        # Create empty QC tables (file_schemas is created automatically by GraphDatabase)
        db.conn.execute("""
            CREATE TABLE dangling_edges (subject VARCHAR, predicate VARCHAR, object VARCHAR);
            CREATE TABLE singleton_nodes (id VARCHAR, category VARCHAR, name VARCHAR);
            CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, name VARCHAR);
        """)

    return db_path


@pytest.fixture
def database_with_dangling_edges(temp_dir):
    """Create a database with dangling edges."""
    db_path = temp_dir / "dangling.duckdb"

    with GraphDatabase(db_path) as db:
        # Create nodes
        db.conn.execute("""
            CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR);
            INSERT INTO nodes VALUES 
                ('HGNC:123', 'biolink:Gene', 'gene1'),
                ('HGNC:456', 'biolink:Gene', 'gene2');
        """)

        # Create edges with some dangling references
        db.conn.execute("""
            CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR);
            INSERT INTO edges VALUES 
                ('HGNC:123', 'biolink:related_to', 'HGNC:456'),  -- Valid
                ('HGNC:123', 'biolink:related_to', 'MISSING:001'),  -- Dangling object
                ('MISSING:002', 'biolink:causes', 'HGNC:456'),  -- Dangling subject
                ('MISSING:003', 'biolink:related_to', 'MISSING:004');  -- Both dangling
        """)

        # Create empty QC tables (file_schemas is created automatically by GraphDatabase)
        db.conn.execute("""
            CREATE TABLE dangling_edges (subject VARCHAR, predicate VARCHAR, object VARCHAR);
            CREATE TABLE singleton_nodes (id VARCHAR, category VARCHAR, name VARCHAR);
            CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, name VARCHAR);
        """)

    return db_path


@pytest.fixture
def database_with_singletons(temp_dir):
    """Create a database with singleton nodes."""
    db_path = temp_dir / "singletons.duckdb"

    with GraphDatabase(db_path) as db:
        # Create nodes including singletons
        db.conn.execute("""
            CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR);
            INSERT INTO nodes VALUES 
                ('HGNC:123', 'biolink:Gene', 'gene1'),  -- Connected
                ('HGNC:456', 'biolink:Gene', 'gene2'),  -- Connected
                ('HGNC:789', 'biolink:Gene', 'gene3'),  -- Singleton
                ('MONDO:001', 'biolink:Disease', 'disease1');  -- Connected
        """)

        # Create edges that don't reference all nodes
        db.conn.execute("""
            CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR);
            INSERT INTO edges VALUES 
                ('HGNC:123', 'biolink:related_to', 'MONDO:001'),
                ('HGNC:456', 'biolink:causes', 'MONDO:001');
        """)

        # Create empty QC tables (file_schemas is created automatically by GraphDatabase)
        db.conn.execute("""
            CREATE TABLE dangling_edges (subject VARCHAR, predicate VARCHAR, object VARCHAR);
            CREATE TABLE singleton_nodes (id VARCHAR, category VARCHAR, name VARCHAR);
            CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, name VARCHAR);
        """)

    return db_path


@pytest.fixture
def database_with_edges_having_original_columns(temp_dir):
    """Create a database where edges have original_subject/original_object columns."""
    db_path = temp_dir / "normalized.duckdb"

    with GraphDatabase(db_path) as db:
        # Create nodes
        db.conn.execute("""
            CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR);
            INSERT INTO nodes VALUES 
                ('CANONICAL:123', 'biolink:Gene', 'gene1'),
                ('CANONICAL:456', 'biolink:Gene', 'gene2');
        """)

        # Create edges with original columns (as if normalized)
        db.conn.execute("""
            CREATE TABLE edges (
                subject VARCHAR, 
                predicate VARCHAR, 
                object VARCHAR,
                original_subject VARCHAR,
                original_object VARCHAR
            );
            INSERT INTO edges VALUES 
                ('CANONICAL:123', 'biolink:related_to', 'CANONICAL:456', 'ORIG:123', 'ORIG:456'),
                ('CANONICAL:123', 'biolink:causes', 'MISSING:001', 'ORIG:123', 'ORIG:MISSING');
        """)

        # Create empty QC tables
        db.conn.execute("""
            CREATE TABLE dangling_edges (
                subject VARCHAR, 
                predicate VARCHAR, 
                object VARCHAR,
                original_subject VARCHAR,
                original_object VARCHAR
            );
            CREATE TABLE singleton_nodes (id VARCHAR, category VARCHAR, name VARCHAR);
            CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, name VARCHAR);
        """)

    return db_path


class TestPruneOperation:
    """Test prune operation functionality."""

    def test_prune_clean_graph_no_changes(self, database_with_clean_graph):
        """Test pruning a clean graph with no dangling edges or singletons."""
        config = PruneConfig(
            database_path=database_with_clean_graph,
            keep_singletons=True,
            remove_singletons=False,
            quiet=True,
            show_progress=False,
        )

        result = prune_graph(config)

        assert result is not None
        assert result.dangling_edges_moved == 0
        assert result.singleton_nodes_moved == 0
        assert result.singleton_nodes_kept == 0
        assert result.final_stats.nodes == 3
        assert result.final_stats.edges == 2
        assert result.final_stats.dangling_edges == 0

    def test_prune_dangling_edges(self, database_with_dangling_edges):
        """Test pruning dangling edges."""
        config = PruneConfig(
            database_path=database_with_dangling_edges,
            keep_singletons=True,
            remove_singletons=False,
            quiet=True,
            show_progress=False,
        )

        result = prune_graph(config)

        assert result is not None
        assert result.dangling_edges_moved == 3  # 3 edges with dangling references
        assert result.final_stats.nodes == 2  # Original nodes remain
        assert result.final_stats.edges == 1  # Only 1 valid edge remains
        assert result.final_stats.dangling_edges == 3  # 3 moved to dangling_edges table

        # Verify dangling edges were moved to separate table
        with GraphDatabase(database_with_dangling_edges) as db:
            dangling_count = db.conn.execute("SELECT COUNT(*) FROM dangling_edges").fetchone()[0]
            assert dangling_count == 3

            # Verify remaining edge is valid
            remaining_edges = db.conn.execute("SELECT * FROM edges").fetchall()
            assert len(remaining_edges) == 1
            assert remaining_edges[0] == ("HGNC:123", "biolink:related_to", "HGNC:456")

    def test_prune_singleton_nodes_keep(self, database_with_singletons):
        """Test pruning with singleton nodes kept."""
        config = PruneConfig(
            database_path=database_with_singletons,
            keep_singletons=True,
            remove_singletons=False,
            quiet=True,
            show_progress=False,
        )

        result = prune_graph(config)

        assert result is not None
        assert result.singleton_nodes_moved == 0
        assert result.singleton_nodes_kept == 1  # HGNC:789 is singleton
        assert result.final_stats.nodes == 4  # All nodes kept
        assert result.final_stats.singleton_nodes == 0  # None moved to singleton table

    def test_prune_singleton_nodes_remove(self, database_with_singletons):
        """Test pruning with singleton nodes removed."""
        config = PruneConfig(
            database_path=database_with_singletons,
            keep_singletons=False,
            remove_singletons=True,
            quiet=True,
            show_progress=False,
        )

        result = prune_graph(config)

        assert result is not None
        assert result.singleton_nodes_moved == 1  # HGNC:789 moved
        assert result.singleton_nodes_kept == 0
        assert result.final_stats.nodes == 3  # Singleton removed from main table
        assert result.final_stats.singleton_nodes == 1  # 1 moved to singleton table

        # Verify singleton was moved to separate table
        with GraphDatabase(database_with_singletons) as db:
            singleton_count = db.conn.execute("SELECT COUNT(*) FROM singleton_nodes").fetchone()[0]
            assert singleton_count == 1

            # Verify singleton was removed from main nodes table
            remaining_node_ids = db.conn.execute("SELECT id FROM nodes").fetchall()
            remaining_ids = {row[0] for row in remaining_node_ids}
            assert "HGNC:789" not in remaining_ids
            assert "HGNC:123" in remaining_ids
            assert "HGNC:456" in remaining_ids
            assert "MONDO:001" in remaining_ids

    def test_prune_with_original_columns_preserved(self, database_with_edges_having_original_columns):
        """Test that original_subject/original_object columns are preserved when moving dangling edges."""
        config = PruneConfig(
            database_path=database_with_edges_having_original_columns,
            keep_singletons=True,
            remove_singletons=False,
            quiet=True,
            show_progress=False,
        )

        result = prune_graph(config)

        assert result is not None
        assert result.dangling_edges_moved == 1  # One edge with missing object

        # Verify original columns were preserved in dangling_edges table
        with GraphDatabase(database_with_edges_having_original_columns) as db:
            dangling_edges = db.conn.execute("""
                SELECT subject, object, original_subject, original_object 
                FROM dangling_edges
            """).fetchall()

            assert len(dangling_edges) == 1
            dangling_edge = dangling_edges[0]
            assert dangling_edge[2] == "ORIG:123"  # original_subject preserved
            assert dangling_edge[3] == "ORIG:MISSING"  # original_object preserved

    def test_prune_empty_database(self, temp_dir):
        """Test pruning an empty database."""
        db_path = temp_dir / "empty.duckdb"

        with GraphDatabase(db_path) as db:
            # Create empty tables (file_schemas is created automatically by GraphDatabase)
            db.conn.execute("""
                CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR);
                CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR);
                CREATE TABLE dangling_edges (subject VARCHAR, predicate VARCHAR, object VARCHAR);
                CREATE TABLE singleton_nodes (id VARCHAR, category VARCHAR, name VARCHAR);
                CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, name VARCHAR);
            """)

        config = PruneConfig(
            database_path=db_path, keep_singletons=True, remove_singletons=False, quiet=True, show_progress=False
        )

        result = prune_graph(config)

        assert result is not None
        assert result.dangling_edges_moved == 0
        assert result.singleton_nodes_moved == 0
        assert result.singleton_nodes_kept == 0
        assert result.final_stats.nodes == 0
        assert result.final_stats.edges == 0

    def test_prune_dangling_edges_by_source_analysis(self, temp_dir):
        """Test analysis of dangling edges by source."""
        db_path = temp_dir / "multi_source.duckdb"

        with GraphDatabase(db_path) as db:
            # Create nodes
            db.conn.execute("""
                CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR);
                INSERT INTO nodes VALUES ('HGNC:123', 'biolink:Gene', 'gene1');
            """)

            # Create edges from different sources with dangling references
            db.conn.execute("""
                CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR, source VARCHAR);
                INSERT INTO edges VALUES 
                    ('HGNC:123', 'biolink:related_to', 'MISSING:001', 'source1'),
                    ('MISSING:002', 'biolink:causes', 'HGNC:123', 'source1'),
                    ('MISSING:003', 'biolink:related_to', 'MISSING:004', 'source2');
            """)

            # Create QC tables
            db.conn.execute("""
                CREATE TABLE dangling_edges (subject VARCHAR, predicate VARCHAR, object VARCHAR, source VARCHAR);
                CREATE TABLE singleton_nodes (id VARCHAR, category VARCHAR, name VARCHAR);
                CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, name VARCHAR);
                """)

        config = PruneConfig(
            database_path=db_path, keep_singletons=True, remove_singletons=False, quiet=True, show_progress=False
        )

        result = prune_graph(config)

        assert result is not None
        assert result.dangling_edges_moved == 3

        # Check breakdown by source
        assert "source1" in result.dangling_edges_by_source
        assert "source2" in result.dangling_edges_by_source
        assert result.dangling_edges_by_source["source1"] == 2
        assert result.dangling_edges_by_source["source2"] == 1

        # Check missing nodes analysis
        assert "source1" in result.missing_nodes_by_source
        assert "source2" in result.missing_nodes_by_source


class TestPruneConfigValidation:
    """Test PruneConfig validation."""

    def test_config_validation_database_exists(self, database_with_clean_graph):
        """Test that config validates existing database."""
        config = PruneConfig(database_path=database_with_clean_graph, keep_singletons=True, remove_singletons=False)

        assert config.database_path == database_with_clean_graph

    def test_config_validation_database_not_exists(self, temp_dir):
        """Test that config validation fails for nonexistent database."""
        nonexistent_db = temp_dir / "nonexistent.duckdb"

        with pytest.raises(ValueError, match="Database file not found"):
            PruneConfig(database_path=nonexistent_db, keep_singletons=True, remove_singletons=False)

    def test_config_validation_singleton_options(self, database_with_clean_graph):
        """Test singleton option validation - should reject conflicting options."""
        # Both True should be invalid (conflicting options)
        with pytest.raises(ValueError, match="Cannot both keep and remove singletons"):
            config = PruneConfig(database_path=database_with_clean_graph, keep_singletons=True, remove_singletons=True)

        # Both False should be valid (default behavior)
        config = PruneConfig(database_path=database_with_clean_graph, keep_singletons=False, remove_singletons=False)

        assert config.keep_singletons is False
        assert config.remove_singletons is False


class TestPruneEdgeCases:
    """Test edge cases and error conditions for prune operation."""

    def test_prune_missing_tables(self, temp_dir):
        """Test pruning database with missing required tables."""
        db_path = temp_dir / "incomplete.duckdb"

        with GraphDatabase(db_path) as db:
            # Create only some tables
            db.conn.execute("CREATE TABLE nodes (id VARCHAR, category VARCHAR)")
            # Missing edges table

        config = PruneConfig(
            database_path=db_path, keep_singletons=True, remove_singletons=False, quiet=True, show_progress=False
        )

        # Should handle gracefully
        result = prune_graph(config)

        assert result is not None
        # Might have warnings or different behavior, but shouldn't crash

    def test_prune_with_malformed_edges(self, temp_dir):
        """Test pruning with malformed edge data."""
        db_path = temp_dir / "malformed.duckdb"

        with GraphDatabase(db_path) as db:
            # Create nodes
            db.conn.execute("""
                CREATE TABLE nodes (id VARCHAR, category VARCHAR);
                INSERT INTO nodes VALUES ('HGNC:123', 'biolink:Gene');
            """)

            # Create edges with NULL values
            db.conn.execute("""
                CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR);
                INSERT INTO edges VALUES 
                    ('HGNC:123', 'biolink:related_to', 'HGNC:456'),
                    (NULL, 'biolink:causes', 'HGNC:123'),
                    ('HGNC:123', NULL, 'HGNC:999');
            """)

            # Create QC tables
            db.conn.execute("""
                CREATE TABLE dangling_edges (subject VARCHAR, predicate VARCHAR, object VARCHAR);
                CREATE TABLE singleton_nodes (id VARCHAR, category VARCHAR);
                CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR);
                """)

        config = PruneConfig(
            database_path=db_path, keep_singletons=True, remove_singletons=False, quiet=True, show_progress=False
        )

        result = prune_graph(config)

        # Should handle NULL values gracefully
        assert result is not None
        assert result.dangling_edges_moved >= 0

    def test_prune_large_number_of_dangling_edges(self, temp_dir):
        """Test pruning with a large number of dangling edges."""
        db_path = temp_dir / "large.duckdb"

        with GraphDatabase(db_path) as db:
            # Create one valid node
            db.conn.execute("""
                CREATE TABLE nodes (id VARCHAR, category VARCHAR);
                INSERT INTO nodes VALUES ('HGNC:123', 'biolink:Gene');
            """)

            # Create many dangling edges
            db.conn.execute("""
                CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR);
            """)

            # Insert many dangling edges
            for i in range(100):
                db.conn.execute(f"""
                    INSERT INTO edges VALUES ('MISSING:{i}', 'biolink:related_to', 'MISSING:{i + 1000}')
                """)

            # Add one valid edge
            db.conn.execute("""
                INSERT INTO edges VALUES ('HGNC:123', 'biolink:related_to', 'HGNC:123')
            """)

            # Create QC tables
            db.conn.execute("""
                CREATE TABLE dangling_edges (subject VARCHAR, predicate VARCHAR, object VARCHAR);
                CREATE TABLE singleton_nodes (id VARCHAR, category VARCHAR);
                CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR);
                """)

        config = PruneConfig(
            database_path=db_path, keep_singletons=True, remove_singletons=False, quiet=True, show_progress=False
        )

        result = prune_graph(config)

        assert result is not None
        assert result.dangling_edges_moved == 100
        assert result.final_stats.edges == 1  # Only valid edge remains
        assert result.final_stats.dangling_edges == 100


if __name__ == "__main__":
    pytest.main([__file__])
