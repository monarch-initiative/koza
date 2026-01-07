"""
Test suite for join graph operation.
"""

import tempfile
from pathlib import Path

import pytest

from koza.graph_operations import join_graphs, prepare_file_specs_from_paths
from koza.model.graph_operations import FileSpec, JoinConfig, KGXFileType, KGXFormat


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_nodes_tsv_file(temp_dir):
    """Create a sample nodes TSV file."""
    nodes_content = """id	category	name
HGNC:123	biolink:Gene	gene1
HGNC:456	biolink:Gene	gene2
MONDO:001	biolink:Disease	disease1
"""
    nodes_file = temp_dir / "nodes.tsv"
    nodes_file.write_text(nodes_content)
    return nodes_file


@pytest.fixture
def sample_edges_tsv_file(temp_dir):
    """Create a sample edges TSV file."""
    edges_content = """subject	predicate	object	category
HGNC:123	biolink:related_to	MONDO:001	biolink:Association
HGNC:456	biolink:causes	MONDO:001	biolink:Association
"""
    edges_file = temp_dir / "edges.tsv"
    edges_file.write_text(edges_content)
    return edges_file


@pytest.fixture
def sample_nodes_jsonl_file(temp_dir):
    """Create a sample nodes JSONL file."""
    jsonl_content = """{"id": "CHEBI:123", "category": "biolink:ChemicalEntity", "name": "chemical1"}
{"id": "CHEBI:456", "category": "biolink:ChemicalEntity", "name": "chemical2"}
"""
    jsonl_file = temp_dir / "nodes.jsonl"
    jsonl_file.write_text(jsonl_content)
    return jsonl_file

#TODO: Create edge_jsonl. Incorporate it into testing.
#@pytest.fixture
#def sample_edges_jsonl_file(temp_dir):
#    return jsonl_file


class TestJoinOperation:
    """Test join operation functionality."""

    def test_join_single_nodes_file(self, sample_nodes_tsv_file, temp_dir):
        """Test joining a single nodes file."""
        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[FileSpec(path=sample_nodes_tsv_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        assert result is not None
        assert len(result.files_loaded) == 1
        assert result.files_loaded[0].records_loaded == 3
        assert result.final_stats.nodes == 3
        assert result.final_stats.edges == 0
        assert output_db.exists()

    def test_join_nodes_and_edges(self, sample_nodes_tsv_file, sample_edges_tsv_file, temp_dir):
        """Test joining both nodes and edges files."""
        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[FileSpec(path=sample_nodes_tsv_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[FileSpec(path=sample_edges_tsv_file, format=KGXFormat.TSV, file_type=KGXFileType.EDGES)],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        assert result is not None
        assert len(result.files_loaded) == 2
        assert result.final_stats.nodes == 3
        assert result.final_stats.edges == 2
        assert output_db.exists()

    def test_join_multiple_formats(self, sample_nodes_tsv_file, sample_nodes_jsonl_file, temp_dir):
        """Test joining files of different formats."""
        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[
                FileSpec(path=sample_nodes_tsv_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES),
                FileSpec(path=sample_nodes_jsonl_file, format=KGXFormat.JSONL, file_type=KGXFileType.NODES),
            ],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        assert result is not None
        assert len(result.files_loaded) == 2
        # Should have 3 TSV nodes + 2 JSONL nodes = 5 total
        assert result.final_stats.nodes == 5
        assert result.final_stats.edges == 0

    def test_join_in_memory_database(self, sample_nodes_tsv_file):
        """Test joining with in-memory database (no output file)."""
        config = JoinConfig(
            node_files=[FileSpec(path=sample_nodes_tsv_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            output_database=None,  # In-memory
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        assert result is not None
        assert len(result.files_loaded) == 1
        assert result.final_stats.nodes == 3
        assert result.database_path is None  # In-memory

    def test_join_with_schema_reporting(self, sample_nodes_tsv_file, sample_edges_tsv_file, temp_dir):
        """Test join operation with schema reporting enabled."""
        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[FileSpec(path=sample_nodes_tsv_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[FileSpec(path=sample_edges_tsv_file, format=KGXFormat.TSV, file_type=KGXFileType.EDGES)],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=True,
        )

        result = join_graphs(config)

        assert result is not None
        assert result.schema_report is not None
        assert len(result.schema_report) > 0
        # Should have generated schema report file
        schema_file = output_db.parent / f"{output_db.stem}_schema_report.yaml"
        assert schema_file.exists()

    def test_join_empty_files_list(self, temp_dir):
        """Test join with empty files lists."""
        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        # Should complete but with empty results
        assert result is not None
        assert len(result.files_loaded) == 0
        assert result.final_stats.nodes == 0
        assert result.final_stats.edges == 0

    def test_join_nonexistent_file(self, temp_dir):
        """Test join with nonexistent file."""
        output_db = temp_dir / "output.duckdb"
        nonexistent_file = temp_dir / "nonexistent.tsv"

        config = JoinConfig(
            node_files=[FileSpec(path=nonexistent_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        # Should handle gracefully with errors
        assert result is not None
        assert len(result.files_loaded) == 1
        assert len(result.files_loaded[0].errors) > 0
        assert result.files_loaded[0].records_loaded == 0


class TestJoinConfigValidation:
    """Test JoinConfig validation logic."""

    def test_database_path_set_from_output_database(self, temp_dir):
        """Test that database_path is set from output_database."""
        output_db = temp_dir / "test.duckdb"

        config = JoinConfig(node_files=[], edge_files=[], output_database=output_db)

        # Should set database_path from output_database
        assert config.database_path == output_db

    def test_database_path_none_when_output_database_none(self):
        """Test that database_path remains None when output_database is None."""
        config = JoinConfig(node_files=[], edge_files=[], output_database=None)

        # Should remain None for in-memory database
        assert config.database_path is None


class TestPrepareFileSpecsFromPaths:
    """Test prepare_file_specs_from_paths helper function."""
    #TODO: Make code which tests 2 sets of node and edge files.
    def test_prepare_specs_from_file_paths(self, sample_nodes_tsv_file, sample_edges_tsv_file):
        """Test preparing file specs from file paths."""
        node_paths = [str(sample_nodes_tsv_file)]
        edge_paths = [str(sample_edges_tsv_file)]

        node_specs, edge_specs = prepare_file_specs_from_paths(node_paths, edge_paths)

        assert len(node_specs) == 1
        assert len(edge_specs) == 1

        assert node_specs[0].path == sample_nodes_tsv_file
        assert node_specs[0].format == KGXFormat.TSV
        assert node_specs[0].file_type == KGXFileType.NODES

        assert edge_specs[0].path == sample_edges_tsv_file
        assert edge_specs[0].format == KGXFormat.TSV
        assert edge_specs[0].file_type == KGXFileType.EDGES

    def test_prepare_specs_format_detection(self, temp_dir):
        """Test format detection in prepare_file_specs_from_paths."""
        # Create files with different extensions
        tsv_file = temp_dir / "data.tsv"
        jsonl_file = temp_dir / "data.jsonl"
        parquet_file = temp_dir / "data.parquet"

        tsv_file.touch()
        jsonl_file.touch()
        parquet_file.touch()

        node_paths = [str(tsv_file), str(jsonl_file), str(parquet_file)]

        node_specs, _ = prepare_file_specs_from_paths(node_paths, [])

        assert len(node_specs) == 3
        assert node_specs[0].format == KGXFormat.TSV
        assert node_specs[1].format == KGXFormat.JSONL
        assert node_specs[2].format == KGXFormat.PARQUET

    def test_prepare_specs_with_glob_patterns(self, temp_dir):
        """Test prepare_file_specs_from_paths with glob patterns."""
        # Create multiple files
        for i in range(3):
            (temp_dir / f"nodes_{i}.tsv").touch()
            (temp_dir / f"edges_{i}.tsv").touch()

        node_pattern = str(temp_dir / "nodes_*.tsv")
        edge_pattern = str(temp_dir / "edges_*.tsv")

        node_specs, edge_specs = prepare_file_specs_from_paths([node_pattern], [edge_pattern])

        assert len(node_specs) == 3
        assert len(edge_specs) == 3

        # All should be detected as TSV nodes/edges
        for spec in node_specs:
            assert spec.format == KGXFormat.TSV
            assert spec.file_type == KGXFileType.NODES

        for spec in edge_specs:
            assert spec.format == KGXFormat.TSV
            assert spec.file_type == KGXFileType.EDGES

    def test_prepare_specs_empty_lists(self):
        """Test prepare_file_specs_from_paths with empty lists."""
        node_specs, edge_specs = prepare_file_specs_from_paths([], [])

        assert len(node_specs) == 0
        assert len(edge_specs) == 0


class TestJoinOperationEdgeCases:
    """Test edge cases and error conditions for join operation."""

    def test_join_malformed_tsv_file(self, temp_dir):
        """Test join with malformed TSV file."""
        malformed_file = temp_dir / "malformed.tsv"
        malformed_content = """id	category	name
HGNC:123	biolink:Gene	gene1	extra_column
HGNC:456	biolink:Gene
"""  # Inconsistent columns
        malformed_file.write_text(malformed_content)

        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[FileSpec(path=malformed_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        # Should handle gracefully, may load partial data
        assert result is not None
        assert len(result.files_loaded) == 1
        # Might have some records loaded despite malformation
        assert result.files_loaded[0].records_loaded >= 0

    def test_join_empty_file(self, temp_dir):
        """Test join with empty file."""
        empty_file = temp_dir / "empty.tsv"
        empty_file.write_text("")

        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[FileSpec(path=empty_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        assert result is not None
        assert len(result.files_loaded) == 1
        assert result.files_loaded[0].records_loaded == 0

    def test_join_header_only_file(self, temp_dir):
        """Test join with header-only file."""
        header_only_file = temp_dir / "header_only.tsv"
        header_only_file.write_text("id\tcategory\tname\n")

        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[FileSpec(path=header_only_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        assert result is not None
        assert len(result.files_loaded) == 1
        assert result.files_loaded[0].records_loaded == 0
        assert result.final_stats.nodes == 0


class TestMultivaluedFieldHandling:
    """Test multivalued field transformation during join."""

    def test_pipe_delimited_category_becomes_array(self, temp_dir):
        """Test that pipe-delimited category values become arrays."""
        nodes_content = """id\tcategory\tname
HGNC:123\tbiolink:Gene|biolink:NamedThing\tgene1
HGNC:456\tbiolink:Gene\tgene2
"""
        nodes_file = temp_dir / "test_nodes.tsv"
        nodes_file.write_text(nodes_content)

        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[FileSpec(path=nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        assert result is not None

        import duckdb

        conn = duckdb.connect(str(output_db))

        # Check that category column is now VARCHAR[]
        schema = conn.execute("DESCRIBE nodes").fetchall()
        category_type = next(row[1] for row in schema if row[0] == "category")
        assert "[]" in category_type  # Should be VARCHAR[]

        # Check actual values
        results = conn.execute("SELECT id, category FROM nodes ORDER BY id").fetchall()
        assert results[0][1] == ["biolink:Gene", "biolink:NamedThing"]  # Pipe-delimited became array
        assert results[1][1] == ["biolink:Gene"]  # Single value also became array
        conn.close()

    def test_has_evidence_multivalued(self, temp_dir):
        """Test that has_evidence (a known multivalued field) is transformed."""
        edges_content = """id\tsubject\tpredicate\tobject\thas_evidence
edge1\tHGNC:123\tbiolink:related_to\tMONDO:001\tECO:0000269|ECO:0000314
edge2\tHGNC:456\tbiolink:causes\tMONDO:001\tECO:0000501
"""
        edges_file = temp_dir / "test_edges.tsv"
        edges_file.write_text(edges_content)

        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[],
            edge_files=[FileSpec(path=edges_file, format=KGXFormat.TSV, file_type=KGXFileType.EDGES)],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        assert result is not None

        import duckdb

        conn = duckdb.connect(str(output_db))

        # Check that has_evidence is now an array
        results = conn.execute("SELECT id, has_evidence FROM edges ORDER BY id").fetchall()
        assert results[0][1] == ["ECO:0000269", "ECO:0000314"]
        assert results[1][1] == ["ECO:0000501"]
        conn.close()

    def test_non_multivalued_fields_unchanged(self, temp_dir):
        """Test that non-multivalued fields remain as VARCHAR."""
        nodes_content = """id\tname\tdescription
HGNC:123\tgene1\tA gene with pipes|in|description
"""
        nodes_file = temp_dir / "test_nodes.tsv"
        nodes_file.write_text(nodes_content)

        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[FileSpec(path=nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        import duckdb

        conn = duckdb.connect(str(output_db))

        # name and description should remain VARCHAR (not arrays)
        schema = conn.execute("DESCRIBE nodes").fetchall()
        schema_dict = {row[0]: row[1] for row in schema}
        assert schema_dict["name"] == "VARCHAR"
        assert schema_dict["description"] == "VARCHAR"

        # Pipes in description should be preserved as literal string
        results = conn.execute("SELECT description FROM nodes").fetchall()
        assert results[0][0] == "A gene with pipes|in|description"
        conn.close()

    def test_empty_multivalued_field_becomes_null(self, temp_dir):
        """Test that empty multivalued fields become NULL, not empty arrays."""
        nodes_content = """id\tcategory\tsynonym
HGNC:123\tbiolink:Gene\talias1|alias2
HGNC:456\tbiolink:Gene\t
"""
        nodes_file = temp_dir / "test_nodes.tsv"
        nodes_file.write_text(nodes_content)

        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[FileSpec(path=nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
        )

        result = join_graphs(config)

        import duckdb

        conn = duckdb.connect(str(output_db))
        results = conn.execute("SELECT id, synonym FROM nodes ORDER BY id").fetchall()
        assert results[0][1] == ["alias1", "alias2"]
        assert results[1][1] is None  # Empty becomes NULL
        conn.close()


class TestProvidedByHandling:
    """Test provided_by column handling during join."""

    def test_existing_provided_by_replaced_by_default(self, temp_dir):
        """Test that existing provided_by column is replaced when generate_provided_by=True (default)."""
        # Create a nodes file with an existing provided_by column
        nodes_content = """id\tcategory\tname\tprovided_by
HGNC:123\tbiolink:Gene\tgene1\tinfores:hgnc
HGNC:456\tbiolink:Gene\tgene2\tinfores:hgnc
"""
        nodes_file = temp_dir / "hgnc_nodes.tsv"
        nodes_file.write_text(nodes_content)

        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[FileSpec(path=nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
            generate_provided_by=True,  # Default behavior
        )

        result = join_graphs(config)

        assert result is not None
        assert result.final_stats.nodes == 2

        # Query the database to verify provided_by was replaced
        import duckdb

        conn = duckdb.connect(str(output_db))
        # Should have exactly one provided_by column (not provided_by_1)
        schema = conn.execute("DESCRIBE nodes").fetchall()
        column_names = [row[0] for row in schema]
        assert "provided_by" in column_names
        assert "provided_by_1" not in column_names

        # The provided_by values should be the filename-based value, not the original
        provided_by_values = conn.execute("SELECT DISTINCT provided_by FROM nodes").fetchall()
        assert len(provided_by_values) == 1
        assert provided_by_values[0][0] == "hgnc_nodes"  # filename stem
        conn.close()

    def test_existing_provided_by_preserved_when_generate_false(self, temp_dir):
        """Test that existing provided_by column is preserved when generate_provided_by=False."""
        # Create a nodes file with an existing provided_by column
        nodes_content = """id\tcategory\tname\tprovided_by
HGNC:123\tbiolink:Gene\tgene1\tinfores:hgnc
HGNC:456\tbiolink:Gene\tgene2\tinfores:mgi
"""
        nodes_file = temp_dir / "mixed_nodes.tsv"
        nodes_file.write_text(nodes_content)

        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[FileSpec(path=nodes_file, format=KGXFormat.TSV, file_type=KGXFileType.NODES)],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
            generate_provided_by=False,  # Preserve original
        )

        result = join_graphs(config)

        assert result is not None
        assert result.final_stats.nodes == 2

        # Query the database to verify provided_by was preserved
        # Note: provided_by is multivalued in Biolink, so values become arrays
        import duckdb

        conn = duckdb.connect(str(output_db))
        # Should have the original provided_by values (as arrays since it's multivalued)
        provided_by_values = conn.execute("SELECT provided_by FROM nodes ORDER BY id").fetchall()
        assert provided_by_values[0][0] == ["infores:hgnc"]
        assert provided_by_values[1][0] == ["infores:mgi"]
        conn.close()

    def test_merge_files_with_and_without_provided_by(self, temp_dir):
        """Test merging files where some have provided_by and some don't."""
        # File with provided_by
        nodes_with_pb = """id\tcategory\tname\tprovided_by
HGNC:123\tbiolink:Gene\tgene1\tinfores:hgnc
"""
        file_with_pb = temp_dir / "with_pb_nodes.tsv"
        file_with_pb.write_text(nodes_with_pb)

        # File without provided_by
        nodes_without_pb = """id\tcategory\tname
MONDO:001\tbiolink:Disease\tdisease1
"""
        file_without_pb = temp_dir / "without_pb_nodes.tsv"
        file_without_pb.write_text(nodes_without_pb)

        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[
                FileSpec(path=file_with_pb, format=KGXFormat.TSV, file_type=KGXFileType.NODES),
                FileSpec(path=file_without_pb, format=KGXFormat.TSV, file_type=KGXFileType.NODES),
            ],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
            generate_provided_by=True,
        )

        result = join_graphs(config)

        assert result is not None
        assert result.final_stats.nodes == 2

        # Query the database to verify no duplicate columns
        import duckdb

        conn = duckdb.connect(str(output_db))
        schema = conn.execute("DESCRIBE nodes").fetchall()
        column_names = [row[0] for row in schema]
        assert "provided_by" in column_names
        assert "provided_by_1" not in column_names

        # Each row should have its filename as provided_by
        results = conn.execute("SELECT id, provided_by FROM nodes ORDER BY id").fetchall()
        # Check that both rows have their respective file source as provided_by
        provided_by_map = {row[0]: row[1] for row in results}
        assert provided_by_map["HGNC:123"] == "with_pb_nodes"
        assert provided_by_map["MONDO:001"] == "without_pb_nodes"
        conn.close()

    def test_jsonl_with_existing_provided_by(self, temp_dir):
        """Test that existing provided_by is replaced in JSONL files too."""
        jsonl_content = """{"id": "CHEBI:123", "category": "biolink:ChemicalEntity", "name": "chemical1", "provided_by": "infores:chebi"}
{"id": "CHEBI:456", "category": "biolink:ChemicalEntity", "name": "chemical2", "provided_by": "infores:chebi"}
"""
        jsonl_file = temp_dir / "chebi_nodes.jsonl"
        jsonl_file.write_text(jsonl_content)

        output_db = temp_dir / "output.duckdb"

        config = JoinConfig(
            node_files=[FileSpec(path=jsonl_file, format=KGXFormat.JSONL, file_type=KGXFileType.NODES)],
            edge_files=[],
            output_database=output_db,
            quiet=True,
            show_progress=False,
            schema_reporting=False,
            generate_provided_by=True,
        )

        result = join_graphs(config)

        assert result is not None
        assert result.final_stats.nodes == 2

        # Query the database to verify provided_by was replaced
        import duckdb

        conn = duckdb.connect(str(output_db))
        schema = conn.execute("DESCRIBE nodes").fetchall()
        column_names = [row[0] for row in schema]
        assert "provided_by" in column_names
        assert "provided_by_1" not in column_names

        # The provided_by values should be the filename-based value
        provided_by_values = conn.execute("SELECT DISTINCT provided_by FROM nodes").fetchall()
        assert len(provided_by_values) == 1
        assert provided_by_values[0][0] == "chebi_nodes"
        conn.close()


if __name__ == "__main__":
    pytest.main([__file__])
