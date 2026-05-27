"""
Test suite for normalize graph operation.
"""

import tempfile
from pathlib import Path

import pytest

from koza.graph_operations import normalize_graph, prepare_mapping_file_specs_from_paths
from koza.graph_operations.utils import GraphDatabase
from koza.model.graph_operations import KGXFormat, NormalizeConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_nodes_file(temp_dir):
    """Create a sample nodes TSV file."""
    nodes_content = """id	category	name
FB:FBgn0000008	biolink:Gene	gene1
FB:FBgn0000014	biolink:Gene	gene2
MONDO:0000001	biolink:Disease	disease1
HGNC:123	biolink:Gene	gene3
"""
    nodes_file = temp_dir / "nodes.tsv"
    nodes_file.write_text(nodes_content)
    return nodes_file


@pytest.fixture
def sample_edges_file(temp_dir):
    """Create a sample edges TSV file."""
    edges_content = """subject	predicate	object	category
FB:FBgn0000008	biolink:related_to	MONDO:0000001	biolink:Association
FB:FBgn0000014	biolink:causes	MONDO:0000001	biolink:Association
HGNC:123	biolink:orthologous_to	FB:FBgn0000008	biolink:Association
"""
    edges_file = temp_dir / "edges.tsv"
    edges_file.write_text(edges_content)
    return edges_file


@pytest.fixture
def sample_sssom_file(temp_dir):
    """Create a sample SSSOM mapping file."""
    sssom_content = """# curie_map:
#   FB: https://flybase.org/reports/
#   NCBIGene: http://purl.uniprot.org/geneid/
#   HGNC: http://identifiers.org/hgnc/
#   skos: http://www.w3.org/2004/02/skos/core#
#   semapv: https://w3id.org/semapv/vocab/
# license: https://creativecommons.org/licenses/by/4.0/
subject_id	predicate_id	object_id	mapping_justification
NCBIGene:43852	skos:exactMatch	FB:FBgn0000008	semapv:UnspecifiedMatching
NCBIGene:42037	skos:exactMatch	FB:FBgn0000014	semapv:UnspecifiedMatching
HGNC:456	skos:exactMatch	HGNC:123	semapv:UnspecifiedMatching
"""
    sssom_file = temp_dir / "mappings.sssom.tsv"
    sssom_file.write_text(sssom_content)
    return sssom_file


@pytest.fixture
def test_database(temp_dir, sample_nodes_file, sample_edges_file):
    """Create a test database with sample data."""
    db_file = temp_dir / "test.duckdb"

    with GraphDatabase(db_file) as db:
        # Load nodes
        db.conn.execute(f"""
            CREATE TABLE nodes AS
            SELECT * FROM read_csv('{sample_nodes_file}', delim='\t', header=true, all_varchar=true)
        """)

        # Load edges
        db.conn.execute(f"""
            CREATE TABLE edges AS
            SELECT * FROM read_csv('{sample_edges_file}', delim='\t', header=true, all_varchar=true)
        """)

    return db_file


def test_prepare_mapping_file_specs_from_paths(sample_sssom_file):
    """Test preparation of mapping file specs."""
    mapping_paths = [sample_sssom_file]

    file_specs = prepare_mapping_file_specs_from_paths(mapping_paths)

    assert len(file_specs) == 1
    assert file_specs[0].path == sample_sssom_file
    assert file_specs[0].format == KGXFormat.TSV
    assert file_specs[0].file_type is None  # Mappings don't have a file type
    assert file_specs[0].source_name == "mappings.sssom"


def test_prepare_mapping_file_specs_with_source_name(sample_sssom_file):
    """Test preparation of mapping file specs with custom source name."""
    mapping_paths = [sample_sssom_file]

    file_specs = prepare_mapping_file_specs_from_paths(mapping_paths, source_name="test_mappings")

    assert len(file_specs) == 1
    assert file_specs[0].source_name == "test_mappings"


def test_prepare_mapping_file_specs_nonexistent_file(temp_dir):
    """Test that nonexistent files raise FileNotFoundError."""
    nonexistent_file = temp_dir / "nonexistent.sssom.tsv"

    with pytest.raises(FileNotFoundError, match="Mapping file not found"):
        prepare_mapping_file_specs_from_paths([nonexistent_file])


def test_normalize_graph_success(test_database, sample_sssom_file):
    """Test successful normalization of graph data."""
    # Prepare mapping file specs
    mapping_specs = prepare_mapping_file_specs_from_paths([sample_sssom_file])

    # Create normalize config
    config = NormalizeConfig(database_path=test_database, mapping_files=mapping_specs, quiet=True, show_progress=False)

    # Execute normalization
    result = normalize_graph(config)

    # Check result
    assert result.success is True
    assert len(result.mappings_loaded) == 1
    assert result.mappings_loaded[0].records_loaded == 3  # 3 mappings in sample file
    assert result.edges_normalized > 0  # Should normalize some edges
    assert result.final_stats is not None
    assert len(result.errors) == 0

    # Verify mappings table was created
    with GraphDatabase(test_database) as db:
        mappings_count = db.conn.execute("SELECT COUNT(*) FROM mappings").fetchone()[0]
        assert mappings_count == 3

        # Check that edges were normalized
        # FB:FBgn0000008 should be normalized to NCBIGene:43852 in subject/object fields
        normalized_edges = db.conn.execute("""
            SELECT subject, object, original_subject, original_object 
            FROM edges 
            WHERE subject = 'NCBIGene:43852' OR object = 'NCBIGene:43852'
        """).fetchall()

        # Should have at least one edge with normalized identifiers
        assert len(normalized_edges) > 0


def test_normalize_graph_no_edges_table(temp_dir, sample_sssom_file):
    """Test normalization with database that has no edges table."""
    # Create database with only nodes table
    db_file = temp_dir / "nodes_only.duckdb"

    with GraphDatabase(db_file) as db:
        db.conn.execute("""
            CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR);
            INSERT INTO nodes VALUES ('TEST:001', 'biolink:Gene', 'test_gene');
        """)

    # Prepare mapping file specs
    mapping_specs = prepare_mapping_file_specs_from_paths([sample_sssom_file])

    # Create normalize config
    config = NormalizeConfig(database_path=db_file, mapping_files=mapping_specs, quiet=True, show_progress=False)

    # Execute normalization
    result = normalize_graph(config)

    # Should succeed but normalize 0 edges
    assert result.success is True
    assert result.edges_normalized == 0
    assert len(result.warnings) == 0  # No warnings expected for this case


def test_normalize_graph_no_tables(temp_dir, sample_sssom_file):
    """Test normalization with database that has no relevant tables."""
    # Create empty database
    db_file = temp_dir / "empty.duckdb"

    with GraphDatabase(db_file) as db:
        pass  # Empty database

    # Prepare mapping file specs
    mapping_specs = prepare_mapping_file_specs_from_paths([sample_sssom_file])

    # Create normalize config
    config = NormalizeConfig(database_path=db_file, mapping_files=mapping_specs, quiet=True, show_progress=False)

    # Execute normalization - should return failed result instead of raising
    result = normalize_graph(config)

    # Should return failed result
    assert result.success is False
    assert "No nodes or edges tables found" in result.summary.message


def test_normalize_config_validation():
    """Test NormalizeConfig validation."""
    # Test missing database file
    with pytest.raises(ValueError, match="Database file not found"):
        NormalizeConfig(database_path=Path("/nonexistent/path.duckdb"), mapping_files=[], quiet=True)


def test_normalize_config_no_mapping_files(test_database):
    """Test NormalizeConfig validation with no mapping files."""
    with pytest.raises(ValueError, match="Must provide at least one SSSOM mapping file"):
        NormalizeConfig(database_path=test_database, mapping_files=[], quiet=True)


def test_sssom_header_handling(temp_dir):
    """Test that SSSOM YAML headers are properly ignored."""
    # Create SSSOM file with complex header
    sssom_content = """# curie_map:
#   FB: https://flybase.org/reports/
#   NCBIGene: http://purl.uniprot.org/geneid/
#   skos: http://www.w3.org/2004/02/skos/core#
#   semapv: https://w3id.org/semapv/vocab/
# license: https://creativecommons.org/licenses/by/4.0/
# mapping_set_id: test_mappings
# mapping_set_version: 1.0
# mapping_date: 2023-01-01
# subject_source: FlyBase
# object_source: NCBIGene
subject_id	predicate_id	object_id	mapping_justification
NCBIGene:12345	skos:exactMatch	FB:FBgn0000001	semapv:UnspecifiedMatching
"""

    sssom_file = temp_dir / "complex_header.sssom.tsv"
    sssom_file.write_text(sssom_content)

    # Create simple database
    db_file = temp_dir / "test.duckdb"
    with GraphDatabase(db_file) as db:
        db.conn.execute("""
            CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR);
            INSERT INTO edges VALUES ('FB:FBgn0000001', 'biolink:related_to', 'TEST:001');
        """)

    # Test loading
    mapping_specs = prepare_mapping_file_specs_from_paths([sssom_file])
    config = NormalizeConfig(database_path=db_file, mapping_files=mapping_specs, quiet=True, show_progress=False)

    result = normalize_graph(config)

    # Should successfully load 1 mapping (ignoring all header lines)
    assert result.success is True
    assert result.mappings_loaded[0].records_loaded == 1

    # Verify the mapping was loaded correctly
    with GraphDatabase(db_file) as db:
        mapping_data = db.conn.execute("""
            SELECT subject_id, object_id FROM mappings
        """).fetchall()

        assert len(mapping_data) == 1
        assert mapping_data[0] == ("NCBIGene:12345", "FB:FBgn0000001")


def test_normalize_with_one_to_many_mappings(temp_dir):
    """
    Test that one-to-many mappings (one object_id to multiple subject_ids)
    are deduplicated to prevent duplicate edge creation.

    This tests the fix for the bug where SSSOM mappings with one-to-many
    relationships would cause the normalization JOIN to create duplicate
    edges with the same UUID but different subject/object values.
    """
    # Create SSSOM file with one-to-many mappings
    # ENSEMBL:ENSCAFG00845030039 maps to BOTH NCBIGene:610515 and NCBIGene:610525
    sssom_content = """# curie_map:
#   NCBIGene: http://identifiers.org/ncbigene/
#   ENSEMBL: http://identifiers.org/ensembl/
#   skos: http://www.w3.org/2004/02/skos/core#
#   semapv: https://w3id.org/semapv/vocab/
subject_id	predicate_id	object_id	mapping_justification
NCBIGene:610515	skos:exactMatch	ENSEMBL:ENSCAFG00845030039	semapv:UnspecifiedMatching
NCBIGene:610525	skos:exactMatch	ENSEMBL:ENSCAFG00845030039	semapv:UnspecifiedMatching
NCBIGene:12345	skos:exactMatch	HGNC:10450	semapv:UnspecifiedMatching
"""
    sssom_file = temp_dir / "one_to_many.sssom.tsv"
    sssom_file.write_text(sssom_content)

    # Create edges file with edges that will be normalized
    edges_content = """id	subject	predicate	object	category
uuid:00daf16d-4d30-11f0-8992-7c1e52c375cf	HGNC:10450	biolink:orthologous_to	ENSEMBL:ENSCAFG00845030039	biolink:GeneToGeneHomologyAssociation
uuid:11111111-1111-1111-1111-111111111111	TEST:001	biolink:related_to	TEST:002	biolink:Association
uuid:22222222-2222-2222-2222-222222222222	HGNC:10450	biolink:interacts_with	TEST:003	biolink:Association
"""
    edges_file = temp_dir / "edges.tsv"
    edges_file.write_text(edges_content)

    # Create database with edges
    db_file = temp_dir / "test_one_to_many.duckdb"
    with GraphDatabase(db_file) as db:
        db.conn.execute(f"""
            CREATE TABLE edges AS
            SELECT * FROM read_csv('{edges_file}', delim='\t', header=true, all_varchar=true)
        """)

    # Get original edge count
    with GraphDatabase(db_file) as db:
        original_edge_count = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

    # Run normalization
    mapping_specs = prepare_mapping_file_specs_from_paths([sssom_file])
    config = NormalizeConfig(
        database_path=db_file,
        mapping_files=mapping_specs,
        quiet=True,
        show_progress=False
    )

    result = normalize_graph(config)

    # Verify success
    assert result.success is True

    # Verify warning about duplicate mappings was generated
    assert len(result.warnings) == 1
    assert "duplicate mappings" in result.warnings[0].lower()

    # Verify edge count remains the same (no duplicates created)
    with GraphDatabase(db_file) as db:
        final_edge_count = db.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

        # Edge count should be exactly the same as before normalization
        assert final_edge_count == original_edge_count, (
            f"Edge count changed from {original_edge_count} to {final_edge_count}. "
            "One-to-many mappings should not create duplicate edges."
        )

        # Verify no duplicate edge IDs exist
        duplicate_ids = db.conn.execute("""
            SELECT id, COUNT(*) as cnt
            FROM edges
            GROUP BY id
            HAVING COUNT(*) > 1
        """).fetchall()

        assert len(duplicate_ids) == 0, (
            f"Found {len(duplicate_ids)} duplicate edge IDs. "
            f"Duplicate IDs: {[row[0] for row in duplicate_ids]}"
        )

        # Verify mappings table was deduplicated
        mappings_count = db.conn.execute("SELECT COUNT(*) FROM mappings").fetchone()[0]
        unique_object_ids = db.conn.execute(
            "SELECT COUNT(DISTINCT object_id) FROM mappings"
        ).fetchone()[0]

        # Should have exactly one mapping per object_id
        assert mappings_count == unique_object_ids, (
            f"Mappings table has {mappings_count} rows but only {unique_object_ids} unique object_ids. "
            "Mappings should be deduplicated by object_id."
        )

        # Verify the edge was normalized (object should be changed to one of the NCBIGene IDs)
        normalized_edge = db.conn.execute("""
            SELECT subject, object, original_object
            FROM edges
            WHERE id = 'uuid:00daf16d-4d30-11f0-8992-7c1e52c375cf'
        """).fetchone()

        assert normalized_edge is not None
        # Object should be normalized to one of the NCBIGene IDs
        assert normalized_edge[1].startswith("NCBIGene:"), (
            f"Object should be normalized to NCBIGene:* but got {normalized_edge[1]}"
        )
        # Original object should be preserved
        assert normalized_edge[2] == "ENSEMBL:ENSCAFG00845030039", (
            f"Original object should be preserved but got {normalized_edge[2]}"
        )


if __name__ == "__main__":
    pytest.main([__file__])
