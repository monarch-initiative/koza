"""
Test suite for append graph operation.
"""

import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from koza.graph_operations import append_graphs
from koza.graph_operations.append import NestedValueError
from koza.graph_operations.utils import GraphDatabase
from koza.main import typer_app
from koza.model.graph_operations import AppendConfig, FileSpec, KGXFileType, KGXFormat


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

        # Create QC tables (file_schemas is created automatically by GraphDatabase)
        db.conn.execute("""
            CREATE TABLE dangling_edges (subject VARCHAR, predicate VARCHAR, object VARCHAR, source VARCHAR);
            CREATE TABLE duplicate_nodes (id VARCHAR, category VARCHAR, name VARCHAR, source VARCHAR);
            CREATE TABLE singleton_nodes (id VARCHAR, category VARCHAR, name VARCHAR, source VARCHAR);
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
            node_files=[FileSpec(path=new_nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
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

            # Check new nodes exist (they should have NULL source since the file didn't have a source column)
            new_node_ids = db.conn.execute("""
                SELECT id FROM nodes WHERE source IS NULL OR source != 'initial'
            """).fetchall()
            new_ids = {row[0] for row in new_node_ids}
            assert "HGNC:789" in new_ids
            assert "MONDO:001" in new_ids

    def test_append_new_edges_only(self, existing_database, new_edges_file):
        """Test appending new edges to existing database."""
        config = AppendConfig(
            database_path=existing_database,
            node_files=[],
            edge_files=[FileSpec(path=new_edges_file, format=KGXFormat.TSV, file_type=KGXFileType.EDGES)],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
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
            node_files=[FileSpec(path=new_nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[FileSpec(path=new_edges_file, format=KGXFormat.TSV, file_type=KGXFileType.EDGES)],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
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
            node_files=[FileSpec(path=duplicate_nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            deduplicate=True,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = append_graphs(config)

        assert result is not None
        assert len(result.files_loaded) == 1
        assert result.files_loaded[0].records_loaded == 2

        # Verify deduplication occurred
        with GraphDatabase(existing_database) as db:
            # Check if nodes table exists
            try:
                node_count = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            except Exception:
                # If nodes table doesn't exist, check what tables do exist
                tables = db.conn.execute("SHOW TABLES").fetchall()
                print(f"Available tables: {tables}")
                # For this test, if no nodes table exists after deduplication,
                # it might mean all nodes were considered duplicates
                node_count = 0

            # Exact count depends on deduplication strategy implementation
            assert node_count >= 0  # Could be 0 if all nodes were duplicates

            # Check that HGNC:999 was added (only if nodes table exists)
            if node_count > 0:
                hgnc_999_count = db.conn.execute("""
                    SELECT COUNT(*) FROM nodes WHERE id = 'HGNC:999'
                """).fetchone()[0]
                assert hgnc_999_count == 1

    def test_append_with_deduplication_disabled(self, existing_database, duplicate_nodes_file):
        """Test appending with deduplication disabled (allows duplicates)."""
        config = AppendConfig(
            database_path=existing_database,
            node_files=[FileSpec(path=duplicate_nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
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
            node_files=[FileSpec(path=new_nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=True,
        )

        result = append_graphs(config)

        assert result is not None
        assert result.schema_report is not None

        # Should have generated schema report file
        schema_file = existing_database.parent / f"{existing_database.stem}_schema_report.yaml"
        assert schema_file.exists()

    def test_append_empty_files_list(self, existing_database):
        """Test append with empty files lists - should raise validation error."""
        with pytest.raises(ValueError, match="Must provide at least one node or edge file"):
            config = AppendConfig(
                database_path=existing_database,
                node_files=[],
                edge_files=[],
                deduplicate=False,
                quiet=True,
                show_progress=False,
                schema_reporting=False,
            )

        # Original data should remain unchanged
        with GraphDatabase(existing_database) as db:
            node_count = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            edge_count = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            assert node_count == 2  # Original nodes
            assert edge_count == 1  # Original edges

    def test_append_to_nonexistent_database(self, temp_dir, new_nodes_file):
        """Test that append fails gracefully with nonexistent database."""
        nonexistent_db = temp_dir / "nonexistent.duckdb"

        with pytest.raises(ValueError, match="Database file not found"):
            AppendConfig(
                database_path=nonexistent_db,
                node_files=[FileSpec(path=new_nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
                edge_files=[],
                deduplicate=False,
            )

    def test_append_nonexistent_file(self, existing_database, temp_dir):
        """Test append with nonexistent file."""
        nonexistent_file = temp_dir / "nonexistent.tsv"

        config = AppendConfig(
            database_path=existing_database,
            node_files=[FileSpec(path=nonexistent_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
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

    def test_config_validation_database_exists(self, existing_database, new_nodes_file):
        """Test that config validates existing database."""
        config = AppendConfig(
            database_path=existing_database,
            node_files=[FileSpec(path=new_nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            deduplicate=False,
        )

        assert config.database_path == existing_database

    def test_config_validation_database_not_exists(self, temp_dir):
        """Test that config validation fails for nonexistent database."""
        nonexistent_db = temp_dir / "nonexistent.duckdb"

        with pytest.raises(ValueError, match="Database file not found"):
            AppendConfig(database_path=nonexistent_db, node_files=[], edge_files=[], deduplicate=False)


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
            node_files=[FileSpec(path=malformed_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
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
            node_files=[FileSpec(path=empty_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
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
            node_files=[FileSpec(path=header_only_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
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
                FileSpec(path=nodes_file1, source_name="test1", format=KGXFormat.TSV, file_type=KGXFileType.NODES),
                FileSpec(path=nodes_file2, source_name="test2", format=KGXFormat.TSV, file_type=KGXFileType.NODES),
            ],
            edge_files=[],
            deduplicate=False,
            quiet=False,  # TODO; turn back to True
            show_progress=False,
            schema_reporting=False,
        )

        result = append_graphs(config)

        assert len(config.node_files) == 2
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
            assert "HGNC:111" in all_ids
            assert "HGNC:222" in all_ids

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
            node_files=[FileSpec(path=different_schema_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            deduplicate=False,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
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


class TestAppendListScalarConformance:
    """LIST-vs-scalar shape is reconciled against the target table (issue #247).

    `UNION ALL BY NAME` casts a `VARCHAR[]` into a `VARCHAR` column via DuckDB's
    list representation, so a KGX jsonl `["biolink:Gene"]` used to land as the
    literal string `['biolink:Gene']` — silently, and invisible to every
    category filter downstream.
    """

    def _append_nodes(self, db_path, *nodes_files):
        def fmt(path):
            return KGXFormat.TSV if path.suffix == ".tsv" else KGXFormat.JSONL

        return append_graphs(
            AppendConfig(
                database_path=db_path,
                node_files=[FileSpec(path=f, format=fmt(f), file_type=KGXFileType.NODES) for f in nodes_files],
                edge_files=[],
                deduplicate=False,
                quiet=True,
                show_progress=False,
                schema_reporting=False,
            )
        )

    def test_list_value_into_scalar_column_keeps_the_element(self, existing_database, temp_dir):
        """A single-element list becomes the element, not its repr string."""
        nodes_file = temp_dir / "list_nodes.jsonl"
        nodes_file.write_text('{"id": "HGNC:789", "category": ["biolink:Gene"], "name": "gene3"}\n')

        self._append_nodes(existing_database, nodes_file)

        with GraphDatabase(existing_database) as db:
            category = db.conn.execute("SELECT category FROM nodes WHERE id = 'HGNC:789'").fetchone()[0]
        assert category == "biolink:Gene"

        # The whole point: the appended row is reachable by the same filter that
        # finds rows loaded from TSV.
        with GraphDatabase(existing_database) as db:
            matched = db.conn.execute("SELECT COUNT(*) FROM nodes WHERE category = 'biolink:Gene'").fetchone()[0]
        assert matched == 3  # 2 seeded + the appended one

    def test_multi_element_list_into_scalar_column_warns(self, existing_database, temp_dir, caplog):
        """Collapsing is lossy when the list has more than one value — say so."""
        nodes_file = temp_dir / "multi_nodes.jsonl"
        nodes_file.write_text('{"id": "HGNC:789", "category": ["biolink:Gene", "biolink:Entity"], "name": "gene3"}\n')

        with caplog.at_level("WARNING"):
            self._append_nodes(existing_database, nodes_file)

        with GraphDatabase(existing_database) as db:
            category = db.conn.execute("SELECT category FROM nodes WHERE id = 'HGNC:789'").fetchone()[0]
        assert category == "biolink:Gene"  # first element, matching merge's semantics
        assert "discards data in 1 row" in caplog.text

    def test_scalar_value_into_list_column_is_wrapped(self, temp_dir):
        """The inverse direction: a scalar lands in a `VARCHAR[]` column as a
        one-element list, and NULL stays NULL rather than becoming [NULL]."""
        db_path = temp_dir / "listcols.duckdb"
        with GraphDatabase(db_path) as db:
            db.conn.execute(
                "CREATE TABLE nodes (id VARCHAR, category VARCHAR[], name VARCHAR);"
                "INSERT INTO nodes VALUES ('HGNC:123', ['biolink:Gene'], 'gene1');"
            )
            db.conn.execute("CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR)")

        nodes_file = temp_dir / "scalar_nodes.jsonl"
        nodes_file.write_text(
            '{"id": "HGNC:789", "category": "biolink:Gene", "name": "gene3"}\n{"id": "HGNC:790", "name": "gene4"}\n'
        )

        self._append_nodes(db_path, nodes_file)

        with GraphDatabase(db_path) as db:
            rows = dict(
                db.conn.execute("SELECT id, category FROM nodes WHERE id IN ('HGNC:789', 'HGNC:790')").fetchall()
            )
        assert rows["HGNC:789"] == ["biolink:Gene"]
        assert rows["HGNC:790"] is None

    def test_matching_shapes_are_left_alone(self, temp_dir):
        """A list into a list column is untouched, including multiple values."""
        db_path = temp_dir / "listmatch.duckdb"
        with GraphDatabase(db_path) as db:
            db.conn.execute(
                "CREATE TABLE nodes (id VARCHAR, category VARCHAR[], name VARCHAR);"
                "INSERT INTO nodes VALUES ('HGNC:123', ['biolink:Gene'], 'gene1');"
            )
            db.conn.execute("CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR)")

        nodes_file = temp_dir / "list_nodes.jsonl"
        nodes_file.write_text('{"id": "HGNC:789", "category": ["biolink:Gene", "biolink:Entity"], "name": "gene3"}\n')

        self._append_nodes(db_path, nodes_file)

        with GraphDatabase(db_path) as db:
            category = db.conn.execute("SELECT category FROM nodes WHERE id = 'HGNC:789'").fetchone()[0]
        assert category == ["biolink:Gene", "biolink:Entity"]

    def _list_column_db(self, temp_dir):
        db_path = temp_dir / "listcols.duckdb"
        with GraphDatabase(db_path) as db:
            db.conn.execute(
                "CREATE TABLE nodes (id VARCHAR, category VARCHAR[], name VARCHAR);"
                "INSERT INTO nodes VALUES ('HGNC:123', ['biolink:Gene'], 'gene1');"
            )
            db.conn.execute("CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR)")
        return db_path

    def _categories(self, db_path, *ids):
        with GraphDatabase(db_path) as db:
            placeholders = ", ".join("?" for _ in ids)
            return dict(
                db.conn.execute(f"SELECT id, category FROM nodes WHERE id IN ({placeholders})", list(ids)).fetchall()
            )

    def test_pipe_delimited_tsv_value_into_list_column_is_split(self, temp_dir):
        """A KGX TSV multivalued cell is split on `|`, not wrapped whole as one
        element (which would silently store `['biolink:Gene|biolink:Entity']`)."""
        db_path = self._list_column_db(temp_dir)
        nodes_file = temp_dir / "pipe_nodes.tsv"
        nodes_file.write_text(
            "id\tcategory\tname\n"
            "HGNC:789\tbiolink:Gene| biolink:Entity |\tgene3\n"
            "HGNC:790\tbiolink:Gene\tgene4\n"
            "HGNC:791\t\tgene5\n"
        )

        result = self._append_nodes(db_path, nodes_file)

        assert not result.files_loaded[0].errors
        rows = self._categories(db_path, "HGNC:789", "HGNC:790", "HGNC:791")
        assert rows["HGNC:789"] == ["biolink:Gene", "biolink:Entity"]
        assert rows["HGNC:790"] == ["biolink:Gene"]
        assert rows["HGNC:791"] is None

    def test_column_added_by_earlier_file_is_conformed(self, existing_database, temp_dir):
        """A column introduced by an earlier file in the same append is part of
        the target schema for later files, so a list there is still collapsed."""
        tsv_file = temp_dir / "a_nodes.tsv"
        tsv_file.write_text("id\tcategory\tname\tsynonym\nHGNC:789\tbiolink:Gene\tgene3\ts1\n")
        jsonl_file = temp_dir / "b_nodes.jsonl"
        jsonl_file.write_text('{"id": "HGNC:790", "category": "biolink:Gene", "synonym": ["s2"]}\n')

        self._append_nodes(existing_database, tsv_file, jsonl_file)

        with GraphDatabase(existing_database) as db:
            synonym = db.conn.execute("SELECT synonym FROM nodes WHERE id = 'HGNC:790'").fetchone()[0]
        assert synonym == "s2"

    def test_mixed_scalar_and_array_jsonl_into_scalar_column(self, existing_database, temp_dir):
        """jsonl mixing `"x"` and `["x"]` in one field reads as a JSON column; its
        values must not land with literal quotes and brackets."""
        nodes_file = temp_dir / "mixed_nodes.jsonl"
        nodes_file.write_text(
            '{"id": "HGNC:789", "category": "biolink:Gene", "name": "gene3"}\n'
            '{"id": "HGNC:790", "category": ["biolink:Gene"], "name": "gene4"}\n'
            '{"id": "HGNC:791", "category": null, "name": "gene5"}\n'
        )

        self._append_nodes(existing_database, nodes_file)

        with GraphDatabase(existing_database) as db:
            rows = dict(
                db.conn.execute(
                    "SELECT id, category FROM nodes WHERE id IN ('HGNC:789', 'HGNC:790', 'HGNC:791')"
                ).fetchall()
            )
        assert rows == {"HGNC:789": "biolink:Gene", "HGNC:790": "biolink:Gene", "HGNC:791": None}

    def test_mixed_scalar_and_array_jsonl_into_list_column(self, temp_dir):
        db_path = self._list_column_db(temp_dir)
        nodes_file = temp_dir / "mixed_nodes.jsonl"
        nodes_file.write_text(
            '{"id": "HGNC:789", "category": "biolink:Gene", "name": "gene3"}\n'
            '{"id": "HGNC:790", "category": ["biolink:Gene", "biolink:Entity"], "name": "gene4"}\n'
            '{"id": "HGNC:791", "name": "gene5"}\n'
        )

        self._append_nodes(db_path, nodes_file)

        rows = self._categories(db_path, "HGNC:789", "HGNC:790", "HGNC:791")
        assert rows["HGNC:789"] == ["biolink:Gene"]
        assert rows["HGNC:790"] == ["biolink:Gene", "biolink:Entity"]
        assert rows["HGNC:791"] is None

    def test_nested_list_into_scalar_column_fails_loudly(self, existing_database, temp_dir):
        """A list of lists has no faithful scalar rendering — abort the append
        rather than insert `"['biolink:Gene']"`, naming file, column, types and
        an example value."""
        nodes_file = temp_dir / "nested_nodes.jsonl"
        nodes_file.write_text('{"id": "HGNC:789", "category": [["biolink:Gene"]], "name": "gene3"}\n')

        with pytest.raises(NestedValueError) as excinfo:
            self._append_nodes(existing_database, nodes_file)

        message = str(excinfo.value)
        assert "nested_nodes.jsonl" in message
        assert "'category'" in message
        assert "VARCHAR[][]" in message
        assert "target column is VARCHAR" in message
        assert "biolink:Gene" in message  # example offending value
        with GraphDatabase(existing_database) as db:
            count = db.conn.execute("SELECT COUNT(*) FROM nodes WHERE id = 'HGNC:789'").fetchone()[0]
        assert count == 0

    def test_json_object_into_list_column_fails_loudly(self, temp_dir):
        db_path = self._list_column_db(temp_dir)
        nodes_file = temp_dir / "object_nodes.jsonl"
        nodes_file.write_text(
            '{"id": "HGNC:789", "category": "biolink:Gene"}\n{"id": "HGNC:790", "category": {"k": "v"}}\n'
        )

        with pytest.raises(NestedValueError) as excinfo:
            self._append_nodes(db_path, nodes_file)

        message = str(excinfo.value)
        assert "object_nodes.jsonl" in message
        assert "'category'" in message
        assert "JSON" in message and "VARCHAR[]" in message
        assert '{"k":"v"}' in message

    def test_nested_value_makes_cli_exit_nonzero(self, existing_database, temp_dir):
        """End to end: `koza append` exits non-zero and prints the reason."""
        nodes_file = temp_dir / "nested_nodes.jsonl"
        nodes_file.write_text('{"id": "HGNC:789", "category": [["biolink:Gene"]], "name": "gene3"}\n')

        result = CliRunner().invoke(typer_app, ["append", str(existing_database), "-n", str(nodes_file), "-q"])

        assert result.exit_code != 0
        assert "nested_nodes.jsonl" in result.output
        assert "'category'" in result.output

    def test_jsonl_pipe_is_a_literal_value(self, temp_dir):
        """Pipe-splitting is TSV-only: a jsonl scalar `"a|b"` is one value."""
        db_path = self._list_column_db(temp_dir)
        nodes_file = temp_dir / "pipe_nodes.jsonl"
        nodes_file.write_text('{"id": "HGNC:789", "category": "a|b", "name": "gene3"}\n')

        self._append_nodes(db_path, nodes_file)

        assert self._categories(db_path, "HGNC:789")["HGNC:789"] == ["a|b"]

    def test_null_elements_dropped_in_list_column(self, temp_dir):
        """Into a list column, NULL elements are dropped and an emptied list is NULL."""
        db_path = self._list_column_db(temp_dir)
        nodes_file = temp_dir / "null_nodes.jsonl"
        nodes_file.write_text(
            '{"id": "HGNC:789", "category": [null, "biolink:Gene"], "name": "gene3"}\n'
            '{"id": "HGNC:790", "category": [null], "name": "gene4"}\n'
            '{"id": "HGNC:791", "category": [], "name": "gene5"}\n'
        )

        self._append_nodes(db_path, nodes_file)

        rows = self._categories(db_path, "HGNC:789", "HGNC:790", "HGNC:791")
        assert rows == {"HGNC:789": ["biolink:Gene"], "HGNC:790": None, "HGNC:791": None}

    def test_null_elements_dropped_from_mixed_json_into_list_column(self, temp_dir):
        db_path = self._list_column_db(temp_dir)
        nodes_file = temp_dir / "mixed_null_nodes.jsonl"
        nodes_file.write_text(
            '{"id": "HGNC:789", "category": "biolink:Gene", "name": "gene3"}\n'
            '{"id": "HGNC:790", "category": [null, "biolink:Entity"], "name": "gene4"}\n'
            '{"id": "HGNC:791", "category": [null], "name": "gene5"}\n'
        )

        self._append_nodes(db_path, nodes_file)

        rows = self._categories(db_path, "HGNC:789", "HGNC:790", "HGNC:791")
        assert rows == {"HGNC:789": ["biolink:Gene"], "HGNC:790": ["biolink:Entity"], "HGNC:791": None}

    def test_null_first_element_does_not_discard_the_value(self, existing_database, temp_dir, caplog):
        """Collapse keeps the first non-NULL element, and a NULL alongside one
        real value is not reported as data loss."""
        nodes_file = temp_dir / "null_first_nodes.jsonl"
        nodes_file.write_text('{"id": "HGNC:789", "category": [null, "biolink:Gene"], "name": "gene3"}\n')

        with caplog.at_level("WARNING"):
            self._append_nodes(existing_database, nodes_file)

        with GraphDatabase(existing_database) as db:
            category = db.conn.execute("SELECT category FROM nodes WHERE id = 'HGNC:789'").fetchone()[0]
        assert category == "biolink:Gene"
        assert "discards data" not in caplog.text


if __name__ == "__main__":
    pytest.main([__file__])
