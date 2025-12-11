"""
Test suite for deduplicate graph operation.

The deduplicate operation removes duplicate nodes and edges based on ID only.
- Nodes are deduplicated by the 'id' column
- Edges are deduplicated by the 'id' column (skipped if no id column exists)
- When duplicates exist, the first occurrence is kept (ordered by file_source or provided_by)
- ALL rows with duplicate IDs are archived to duplicate_nodes/duplicate_edges tables
"""

import tempfile
from pathlib import Path

import pytest

from koza.graph_operations import deduplicate_graph
from koza.graph_operations.utils import GraphDatabase
from koza.model.graph_operations import DeduplicateConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def database_with_no_duplicates(temp_dir):
    """Create a database with no duplicate nodes or edges."""
    db_path = temp_dir / "clean.duckdb"

    with GraphDatabase(db_path) as db:
        # Create nodes with unique IDs
        db.conn.execute("""
            CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR, file_source VARCHAR);
            INSERT INTO nodes VALUES
                ('HGNC:123', 'biolink:Gene', 'gene1', 'source1'),
                ('HGNC:456', 'biolink:Gene', 'gene2', 'source1'),
                ('MONDO:001', 'biolink:Disease', 'disease1', 'source2');
        """)

        # Create edges with unique IDs
        db.conn.execute("""
            CREATE TABLE edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR, file_source VARCHAR);
            INSERT INTO edges VALUES
                ('edge1', 'HGNC:123', 'biolink:related_to', 'MONDO:001', 'source1'),
                ('edge2', 'HGNC:456', 'biolink:causes', 'MONDO:001', 'source2');
        """)

        # Create empty QC tables
        db.conn.execute("""
            CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, name VARCHAR, file_source VARCHAR);
            CREATE TABLE duplicate_edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR, file_source VARCHAR);
        """)

    return db_path


@pytest.fixture
def database_with_duplicate_nodes(temp_dir):
    """Create a database with duplicate nodes."""
    db_path = temp_dir / "dup_nodes.duckdb"

    with GraphDatabase(db_path) as db:
        # Create nodes with duplicates - same ID, different sources
        db.conn.execute("""
            CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR, file_source VARCHAR);
            INSERT INTO nodes VALUES
                ('HGNC:123', 'biolink:Gene', 'gene1_v1', 'source1'),
                ('HGNC:123', 'biolink:Gene', 'gene1_v2', 'source2'),
                ('HGNC:456', 'biolink:Gene', 'gene2', 'source1'),
                ('MONDO:001', 'biolink:Disease', 'disease1', 'source1'),
                ('MONDO:001', 'biolink:Disease', 'disease1_alt', 'source2'),
                ('MONDO:001', 'biolink:Disease', 'disease1_v3', 'source3');
        """)

        # Create edges (no duplicates for this fixture)
        db.conn.execute("""
            CREATE TABLE edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR, file_source VARCHAR);
            INSERT INTO edges VALUES
                ('edge1', 'HGNC:123', 'biolink:related_to', 'MONDO:001', 'source1');
        """)

        # Create empty QC tables
        db.conn.execute("""
            CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, name VARCHAR, file_source VARCHAR);
            CREATE TABLE duplicate_edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR, file_source VARCHAR);
        """)

    return db_path


@pytest.fixture
def database_with_duplicate_edges(temp_dir):
    """Create a database with duplicate edges."""
    db_path = temp_dir / "dup_edges.duckdb"

    with GraphDatabase(db_path) as db:
        # Create nodes (no duplicates)
        db.conn.execute("""
            CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR, file_source VARCHAR);
            INSERT INTO nodes VALUES
                ('HGNC:123', 'biolink:Gene', 'gene1', 'source1'),
                ('MONDO:001', 'biolink:Disease', 'disease1', 'source1');
        """)

        # Create edges with duplicates
        db.conn.execute("""
            CREATE TABLE edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR, file_source VARCHAR);
            INSERT INTO edges VALUES
                ('edge1', 'HGNC:123', 'biolink:related_to', 'MONDO:001', 'source1'),
                ('edge1', 'HGNC:123', 'biolink:related_to', 'MONDO:001', 'source2'),
                ('edge2', 'HGNC:123', 'biolink:causes', 'MONDO:001', 'source1'),
                ('edge2', 'HGNC:123', 'biolink:causes', 'MONDO:001', 'source2'),
                ('edge2', 'HGNC:123', 'biolink:causes', 'MONDO:001', 'source3');
        """)

        # Create empty QC tables
        db.conn.execute("""
            CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, name VARCHAR, file_source VARCHAR);
            CREATE TABLE duplicate_edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR, file_source VARCHAR);
        """)

    return db_path


@pytest.fixture
def database_with_duplicates_nodes_and_edges(temp_dir):
    """Create a database with duplicate nodes and edges."""
    db_path = temp_dir / "dup_both.duckdb"

    with GraphDatabase(db_path) as db:
        # Create nodes with duplicates
        db.conn.execute("""
            CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR, file_source VARCHAR);
            INSERT INTO nodes VALUES
                ('HGNC:123', 'biolink:Gene', 'gene1_v1', 'source1'),
                ('HGNC:123', 'biolink:Gene', 'gene1_v2', 'source2'),
                ('HGNC:456', 'biolink:Gene', 'gene2', 'source1'),
                ('MONDO:001', 'biolink:Disease', 'disease1', 'source1');
        """)

        # Create edges with duplicates
        db.conn.execute("""
            CREATE TABLE edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR, file_source VARCHAR);
            INSERT INTO edges VALUES
                ('edge1', 'HGNC:123', 'biolink:related_to', 'MONDO:001', 'source1'),
                ('edge1', 'HGNC:123', 'biolink:related_to', 'MONDO:001', 'source2'),
                ('edge2', 'HGNC:456', 'biolink:causes', 'MONDO:001', 'source1');
        """)

        # Create empty QC tables
        db.conn.execute("""
            CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, name VARCHAR, file_source VARCHAR);
            CREATE TABLE duplicate_edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR, file_source VARCHAR);
        """)

    return db_path


@pytest.fixture
def database_with_edges_no_id_column(temp_dir):
    """Create a database where edges have no id column."""
    db_path = temp_dir / "edges_no_id.duckdb"

    with GraphDatabase(db_path) as db:
        # Create nodes with duplicates
        db.conn.execute("""
            CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR, file_source VARCHAR);
            INSERT INTO nodes VALUES
                ('HGNC:123', 'biolink:Gene', 'gene1', 'source1'),
                ('HGNC:123', 'biolink:Gene', 'gene1_dup', 'source2');
        """)

        # Create edges without id column
        db.conn.execute("""
            CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR, file_source VARCHAR);
            INSERT INTO edges VALUES
                ('HGNC:123', 'biolink:related_to', 'HGNC:456', 'source1'),
                ('HGNC:123', 'biolink:causes', 'HGNC:789', 'source2');
        """)

        # Create empty QC tables
        db.conn.execute("""
            CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, name VARCHAR, file_source VARCHAR);
        """)

    return db_path


@pytest.fixture
def database_with_provided_by_ordering(temp_dir):
    """Create a database using provided_by column instead of file_source."""
    db_path = temp_dir / "provided_by.duckdb"

    with GraphDatabase(db_path) as db:
        # Create nodes with duplicates, using provided_by for ordering
        db.conn.execute("""
            CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR, provided_by VARCHAR);
            INSERT INTO nodes VALUES
                ('HGNC:123', 'biolink:Gene', 'gene1_from_b', 'source_b'),
                ('HGNC:123', 'biolink:Gene', 'gene1_from_a', 'source_a'),
                ('HGNC:456', 'biolink:Gene', 'gene2', 'source_a');
        """)

        db.conn.execute("""
            CREATE TABLE edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR, provided_by VARCHAR);
            INSERT INTO edges VALUES
                ('edge1', 'HGNC:123', 'biolink:related_to', 'HGNC:456', 'source_a');
        """)

        db.conn.execute("""
            CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, name VARCHAR, provided_by VARCHAR);
            CREATE TABLE duplicate_edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR, provided_by VARCHAR);
        """)

    return db_path


class TestDeduplicateOperation:
    """Test deduplicate operation functionality (ID-based deduplication)."""

    def test_deduplicate_no_duplicate_ids(self, database_with_no_duplicates):
        """Test deduplicating a database where all IDs are unique."""
        config = DeduplicateConfig(
            database_path=database_with_no_duplicates,
            deduplicate_nodes=True,
            deduplicate_edges=True,
            quiet=True,
            show_progress=False,
        )

        result = deduplicate_graph(config)

        assert result is not None
        assert result.success is True
        assert result.duplicate_nodes_found == 0
        assert result.duplicate_nodes_removed == 0
        assert result.duplicate_edges_found == 0
        assert result.duplicate_edges_removed == 0
        assert result.final_stats.nodes == 3
        assert result.final_stats.edges == 2

    def test_deduplicate_nodes_by_id(self, database_with_duplicate_nodes):
        """Test deduplicating nodes by ID - rows with same ID are removed, first occurrence kept."""
        config = DeduplicateConfig(
            database_path=database_with_duplicate_nodes,
            deduplicate_nodes=True,
            deduplicate_edges=True,
            quiet=True,
            show_progress=False,
        )

        result = deduplicate_graph(config)

        assert result is not None
        assert result.success is True
        # HGNC:123 has 2 rows, MONDO:001 has 3 rows = 5 total duplicate rows
        assert result.duplicate_nodes_found == 5
        # Removed 1 from HGNC:123, 2 from MONDO:001 = 3 removed
        assert result.duplicate_nodes_removed == 3
        # Final count: 3 unique nodes remain
        assert result.final_stats.nodes == 3

        # Verify duplicate_nodes table was populated
        with GraphDatabase(database_with_duplicate_nodes) as db:
            dup_count = db.conn.execute("SELECT COUNT(*) FROM duplicate_nodes").fetchone()[0]
            assert dup_count == 5  # All rows with duplicate IDs archived

            # Verify main nodes table has only unique entries
            remaining = db.conn.execute("SELECT id, name FROM nodes ORDER BY id").fetchall()
            ids = [r[0] for r in remaining]
            assert len(ids) == 3
            assert ids.count("HGNC:123") == 1
            assert ids.count("MONDO:001") == 1
            assert ids.count("HGNC:456") == 1

    def test_deduplicate_edges_by_id(self, database_with_duplicate_edges):
        """Test deduplicating edges by ID - rows with same ID are removed, first occurrence kept."""
        config = DeduplicateConfig(
            database_path=database_with_duplicate_edges,
            deduplicate_nodes=True,
            deduplicate_edges=True,
            quiet=True,
            show_progress=False,
        )

        result = deduplicate_graph(config)

        assert result is not None
        assert result.success is True
        assert result.duplicate_nodes_found == 0
        assert result.duplicate_nodes_removed == 0
        # edge1 has 2 rows, edge2 has 3 rows = 5 total duplicate rows
        assert result.duplicate_edges_found == 5
        # Removed 1 from edge1, 2 from edge2 = 3 removed
        assert result.duplicate_edges_removed == 3
        # Final count: 2 unique edges remain
        assert result.final_stats.edges == 2

        # Verify duplicate_edges table was populated
        with GraphDatabase(database_with_duplicate_edges) as db:
            dup_count = db.conn.execute("SELECT COUNT(*) FROM duplicate_edges").fetchone()[0]
            assert dup_count == 5

            # Verify main edges table has only unique entries
            remaining = db.conn.execute("SELECT id FROM edges ORDER BY id").fetchall()
            ids = [r[0] for r in remaining]
            assert len(ids) == 2
            assert ids.count("edge1") == 1
            assert ids.count("edge2") == 1

    def test_deduplicate_both_nodes_and_edges_by_id(self, database_with_duplicates_nodes_and_edges):
        """Test deduplicating both nodes and edges by their respective IDs."""
        config = DeduplicateConfig(
            database_path=database_with_duplicates_nodes_and_edges,
            deduplicate_nodes=True,
            deduplicate_edges=True,
            quiet=True,
            show_progress=False,
        )

        result = deduplicate_graph(config)

        assert result is not None
        assert result.success is True
        assert result.duplicate_nodes_found == 2  # HGNC:123 has 2 rows
        assert result.duplicate_nodes_removed == 1
        assert result.duplicate_edges_found == 2  # edge1 has 2 rows
        assert result.duplicate_edges_removed == 1
        assert result.final_stats.nodes == 3
        assert result.final_stats.edges == 2

    def test_deduplicate_nodes_only(self, database_with_duplicates_nodes_and_edges):
        """Test deduplicating only nodes, leaving edges untouched."""
        config = DeduplicateConfig(
            database_path=database_with_duplicates_nodes_and_edges,
            deduplicate_nodes=True,
            deduplicate_edges=False,
            quiet=True,
            show_progress=False,
        )

        result = deduplicate_graph(config)

        assert result is not None
        assert result.success is True
        assert result.duplicate_nodes_found == 2
        assert result.duplicate_nodes_removed == 1
        assert result.duplicate_edges_found == 0  # Not processed
        assert result.duplicate_edges_removed == 0
        assert result.final_stats.nodes == 3
        assert result.final_stats.edges == 3  # Edges untouched (still has duplicates)

    def test_deduplicate_edges_only(self, database_with_duplicates_nodes_and_edges):
        """Test deduplicating only edges, leaving nodes untouched."""
        config = DeduplicateConfig(
            database_path=database_with_duplicates_nodes_and_edges,
            deduplicate_nodes=False,
            deduplicate_edges=True,
            quiet=True,
            show_progress=False,
        )

        result = deduplicate_graph(config)

        assert result is not None
        assert result.success is True
        assert result.duplicate_nodes_found == 0  # Not processed
        assert result.duplicate_nodes_removed == 0
        assert result.duplicate_edges_found == 2
        assert result.duplicate_edges_removed == 1
        assert result.final_stats.nodes == 4  # Nodes untouched (still has duplicates)
        assert result.final_stats.edges == 2

    def test_deduplicate_edges_no_id_column(self, database_with_edges_no_id_column):
        """Test that edge deduplication is skipped when edges have no id column."""
        config = DeduplicateConfig(
            database_path=database_with_edges_no_id_column,
            deduplicate_nodes=True,
            deduplicate_edges=True,
            quiet=True,
            show_progress=False,
        )

        result = deduplicate_graph(config)

        assert result is not None
        assert result.success is True
        # Node deduplication should work
        assert result.duplicate_nodes_found == 2
        assert result.duplicate_nodes_removed == 1
        # Edge deduplication should be skipped (no id column)
        assert result.duplicate_edges_found == 0
        assert result.duplicate_edges_removed == 0
        assert result.final_stats.nodes == 1
        assert result.final_stats.edges == 2  # Edges untouched

    def test_deduplicate_same_id_different_content(self, temp_dir):
        """Test that rows with same ID but different content are deduplicated (ID-only matching).

        This verifies that deduplication is based solely on the ID column, NOT on
        the full row content. Two nodes with the same ID but different names/categories
        will be treated as duplicates.
        """
        db_path = temp_dir / "same_id_diff_content.duckdb"

        with GraphDatabase(db_path) as db:
            # Create nodes with same ID but completely different content
            db.conn.execute("""
                CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR, description VARCHAR, file_source VARCHAR);
                INSERT INTO nodes VALUES
                    ('HGNC:123', 'biolink:Gene', 'BRCA1', 'Tumor suppressor', 'source1'),
                    ('HGNC:123', 'biolink:Protein', 'BRCA1_protein', 'Different description', 'source2'),
                    ('HGNC:456', 'biolink:Gene', 'TP53', 'Another gene', 'source1');
                CREATE TABLE edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR, file_source VARCHAR);
                CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, name VARCHAR, description VARCHAR, file_source VARCHAR);
                CREATE TABLE duplicate_edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR, file_source VARCHAR);
            """)

        config = DeduplicateConfig(
            database_path=db_path,
            deduplicate_nodes=True,
            deduplicate_edges=False,
            quiet=True,
            show_progress=False,
        )

        result = deduplicate_graph(config)

        assert result.success is True
        assert result.duplicate_nodes_found == 2  # Both rows for HGNC:123
        assert result.duplicate_nodes_removed == 1
        assert result.final_stats.nodes == 2  # HGNC:123 and HGNC:456

        # Verify the first occurrence was kept (source1, with 'biolink:Gene')
        with GraphDatabase(db_path) as db:
            kept_node = db.conn.execute("SELECT category, name FROM nodes WHERE id = 'HGNC:123'").fetchone()
            assert kept_node[0] == "biolink:Gene"  # First source's category
            assert kept_node[1] == "BRCA1"  # First source's name

    def test_deduplicate_order_by_provided_by(self, database_with_provided_by_ordering):
        """Test that deduplication uses provided_by for ordering when file_source is absent."""
        config = DeduplicateConfig(
            database_path=database_with_provided_by_ordering,
            deduplicate_nodes=True,
            deduplicate_edges=True,
            quiet=True,
            show_progress=False,
        )

        result = deduplicate_graph(config)

        assert result is not None
        assert result.success is True
        assert result.duplicate_nodes_found == 2
        assert result.duplicate_nodes_removed == 1
        assert result.final_stats.nodes == 2

        # Verify the first occurrence (ordered by provided_by) was kept
        with GraphDatabase(database_with_provided_by_ordering) as db:
            node = db.conn.execute("SELECT name FROM nodes WHERE id = 'HGNC:123'").fetchone()
            # source_a comes before source_b alphabetically, so gene1_from_a should be kept
            assert node[0] == "gene1_from_a"


class TestDeduplicateConfigValidation:
    """Test DeduplicateConfig validation."""

    def test_config_validation_database_exists(self, database_with_no_duplicates):
        """Test that config validates existing database."""
        config = DeduplicateConfig(
            database_path=database_with_no_duplicates,
            deduplicate_nodes=True,
            deduplicate_edges=True,
        )

        assert config.database_path == database_with_no_duplicates

    def test_config_validation_database_not_exists(self, temp_dir):
        """Test that config validation fails for nonexistent database."""
        nonexistent_db = temp_dir / "nonexistent.duckdb"

        with pytest.raises(ValueError, match="Database file not found"):
            DeduplicateConfig(database_path=nonexistent_db)

    def test_config_default_values(self, database_with_no_duplicates):
        """Test that config has correct default values."""
        config = DeduplicateConfig(database_path=database_with_no_duplicates)

        assert config.deduplicate_nodes is True
        assert config.deduplicate_edges is True
        assert config.quiet is False
        assert config.show_progress is True


class TestDeduplicateEdgeCases:
    """Test edge cases and error conditions for deduplicate operation."""

    def test_deduplicate_empty_database(self, temp_dir):
        """Test deduplicating an empty database."""
        db_path = temp_dir / "empty.duckdb"

        with GraphDatabase(db_path) as db:
            db.conn.execute("""
                CREATE TABLE nodes (id VARCHAR, category VARCHAR, file_source VARCHAR);
                CREATE TABLE edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR, file_source VARCHAR);
                CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, file_source VARCHAR);
                CREATE TABLE duplicate_edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR, file_source VARCHAR);
            """)

        config = DeduplicateConfig(
            database_path=db_path,
            deduplicate_nodes=True,
            deduplicate_edges=True,
            quiet=True,
            show_progress=False,
        )

        result = deduplicate_graph(config)

        assert result is not None
        assert result.success is True
        assert result.duplicate_nodes_found == 0
        assert result.duplicate_nodes_removed == 0
        assert result.duplicate_edges_found == 0
        assert result.duplicate_edges_removed == 0
        assert result.final_stats.nodes == 0
        assert result.final_stats.edges == 0

    def test_deduplicate_no_nodes_table(self, temp_dir):
        """Test deduplicating database with no nodes table."""
        db_path = temp_dir / "no_nodes.duckdb"

        with GraphDatabase(db_path) as db:
            db.conn.execute("""
                CREATE TABLE edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR, file_source VARCHAR);
                INSERT INTO edges VALUES
                    ('edge1', 'HGNC:123', 'biolink:related_to', 'MONDO:001', 'source1'),
                    ('edge1', 'HGNC:123', 'biolink:related_to', 'MONDO:001', 'source2');
                CREATE TABLE duplicate_edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR, file_source VARCHAR);
            """)

        config = DeduplicateConfig(
            database_path=db_path,
            deduplicate_nodes=True,
            deduplicate_edges=True,
            quiet=True,
            show_progress=False,
        )

        result = deduplicate_graph(config)

        assert result is not None
        assert result.success is True
        # Node deduplication should be skipped gracefully
        assert result.duplicate_nodes_found == 0
        assert result.duplicate_nodes_removed == 0
        # Edge deduplication should work
        assert result.duplicate_edges_found == 2
        assert result.duplicate_edges_removed == 1

    def test_deduplicate_no_edges_table(self, temp_dir):
        """Test deduplicating database with no edges table."""
        db_path = temp_dir / "no_edges.duckdb"

        with GraphDatabase(db_path) as db:
            db.conn.execute("""
                CREATE TABLE nodes (id VARCHAR, category VARCHAR, file_source VARCHAR);
                INSERT INTO nodes VALUES
                    ('HGNC:123', 'biolink:Gene', 'source1'),
                    ('HGNC:123', 'biolink:Gene', 'source2');
                CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, file_source VARCHAR);
            """)

        config = DeduplicateConfig(
            database_path=db_path,
            deduplicate_nodes=True,
            deduplicate_edges=True,
            quiet=True,
            show_progress=False,
        )

        result = deduplicate_graph(config)

        assert result is not None
        assert result.success is True
        # Node deduplication should work
        assert result.duplicate_nodes_found == 2
        assert result.duplicate_nodes_removed == 1
        # Edge deduplication should be skipped gracefully
        assert result.duplicate_edges_found == 0
        assert result.duplicate_edges_removed == 0

    def test_deduplicate_large_number_of_duplicates(self, temp_dir):
        """Test deduplicating with many duplicate entries."""
        db_path = temp_dir / "large.duckdb"

        with GraphDatabase(db_path) as db:
            # Create nodes table
            db.conn.execute("""
                CREATE TABLE nodes (id VARCHAR, category VARCHAR, file_source VARCHAR);
            """)

            # Insert many duplicates of the same ID
            for i in range(100):
                db.conn.execute(f"""
                    INSERT INTO nodes VALUES ('HGNC:123', 'biolink:Gene', 'source{i}')
                """)

            # Also add some unique nodes
            for i in range(50):
                db.conn.execute(f"""
                    INSERT INTO nodes VALUES ('HGNC:{i + 1000}', 'biolink:Gene', 'source1')
                """)

            db.conn.execute("""
                CREATE TABLE edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR, file_source VARCHAR);
                CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, file_source VARCHAR);
                CREATE TABLE duplicate_edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR, file_source VARCHAR);
            """)

        config = DeduplicateConfig(
            database_path=db_path,
            deduplicate_nodes=True,
            deduplicate_edges=True,
            quiet=True,
            show_progress=False,
        )

        result = deduplicate_graph(config)

        assert result is not None
        assert result.success is True
        assert result.duplicate_nodes_found == 100  # All 100 rows for HGNC:123
        assert result.duplicate_nodes_removed == 99  # Keep 1, remove 99
        assert result.final_stats.nodes == 51  # 1 HGNC:123 + 50 unique nodes

    def test_deduplicate_no_ordering_column(self, temp_dir):
        """Test deduplication when neither file_source nor provided_by exists."""
        db_path = temp_dir / "no_order.duckdb"

        with GraphDatabase(db_path) as db:
            db.conn.execute("""
                CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR);
                INSERT INTO nodes VALUES
                    ('HGNC:123', 'biolink:Gene', 'gene1_v1'),
                    ('HGNC:123', 'biolink:Gene', 'gene1_v2'),
                    ('HGNC:456', 'biolink:Gene', 'gene2');
                CREATE TABLE edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR);
                CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, name VARCHAR);
                CREATE TABLE duplicate_edges (id VARCHAR, subject VARCHAR, predicate VARCHAR, object VARCHAR);
            """)

        config = DeduplicateConfig(
            database_path=db_path,
            deduplicate_nodes=True,
            deduplicate_edges=True,
            quiet=True,
            show_progress=False,
        )

        result = deduplicate_graph(config)

        assert result is not None
        assert result.success is True
        assert result.duplicate_nodes_found == 2
        assert result.duplicate_nodes_removed == 1
        assert result.final_stats.nodes == 2  # Only 2 unique nodes

    def test_deduplicate_result_summary(self, database_with_duplicates_nodes_and_edges):
        """Test that result summary is correctly populated."""
        config = DeduplicateConfig(
            database_path=database_with_duplicates_nodes_and_edges,
            deduplicate_nodes=True,
            deduplicate_edges=True,
            quiet=True,
            show_progress=False,
        )

        result = deduplicate_graph(config)

        assert result is not None
        assert result.success is True
        assert result.summary is not None
        assert result.summary.operation == "deduplicate"
        assert result.summary.success is True
        assert result.total_time_seconds >= 0
        assert len(result.errors) == 0


class TestDeduplicateArchiveTables:
    """Test that duplicate data is properly archived."""

    def test_duplicate_nodes_archived_correctly(self, database_with_duplicate_nodes):
        """Test that all duplicate node rows are archived to duplicate_nodes table."""
        config = DeduplicateConfig(
            database_path=database_with_duplicate_nodes,
            deduplicate_nodes=True,
            deduplicate_edges=False,
            quiet=True,
            show_progress=False,
        )

        deduplicate_graph(config)

        with GraphDatabase(database_with_duplicate_nodes) as db:
            # Check that duplicate_nodes contains all rows for duplicate IDs
            dup_rows = db.conn.execute("""
                SELECT id, name, file_source FROM duplicate_nodes ORDER BY id, file_source
            """).fetchall()

            # HGNC:123 had 2 rows, MONDO:001 had 3 rows = 5 total
            assert len(dup_rows) == 5

            # Verify HGNC:123 duplicates
            hgnc_dups = [r for r in dup_rows if r[0] == "HGNC:123"]
            assert len(hgnc_dups) == 2

            # Verify MONDO:001 duplicates
            mondo_dups = [r for r in dup_rows if r[0] == "MONDO:001"]
            assert len(mondo_dups) == 3

    def test_duplicate_edges_archived_correctly(self, database_with_duplicate_edges):
        """Test that all duplicate edge rows are archived to duplicate_edges table."""
        config = DeduplicateConfig(
            database_path=database_with_duplicate_edges,
            deduplicate_nodes=False,
            deduplicate_edges=True,
            quiet=True,
            show_progress=False,
        )

        deduplicate_graph(config)

        with GraphDatabase(database_with_duplicate_edges) as db:
            # Check that duplicate_edges contains all rows for duplicate IDs
            dup_rows = db.conn.execute("""
                SELECT id, file_source FROM duplicate_edges ORDER BY id, file_source
            """).fetchall()

            # edge1 had 2 rows, edge2 had 3 rows = 5 total
            assert len(dup_rows) == 5

            # Verify edge1 duplicates
            edge1_dups = [r for r in dup_rows if r[0] == "edge1"]
            assert len(edge1_dups) == 2

            # Verify edge2 duplicates
            edge2_dups = [r for r in dup_rows if r[0] == "edge2"]
            assert len(edge2_dups) == 3


if __name__ == "__main__":
    pytest.main([__file__])
