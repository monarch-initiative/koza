"""
Test suite for normalize graph operation.
"""

import tempfile
from pathlib import Path

import pytest

from koza.graph_operations import MalformedMappingError, normalize_graph, prepare_mapping_file_specs_from_paths
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
    config = NormalizeConfig(database_path=db_file, mapping_files=mapping_specs, quiet=True, show_progress=False)

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
            f"Found {len(duplicate_ids)} duplicate edge IDs. Duplicate IDs: {[row[0] for row in duplicate_ids]}"
        )

        # Verify mappings table was deduplicated
        mappings_count = db.conn.execute("SELECT COUNT(*) FROM mappings").fetchone()[0]
        unique_object_ids = db.conn.execute("SELECT COUNT(DISTINCT object_id) FROM mappings").fetchone()[0]

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


#
# Predicate (use_match) filtering - https://github.com/monarch-initiative/koza/issues/249
#

MIXED_PREDICATE_SSSOM = """# curie_map:
#   skos: http://www.w3.org/2004/02/skos/core#
#   semapv: https://w3id.org/semapv/vocab/
subject_id	predicate_id	object_id	mapping_justification
NCBIGene:43852	skos:exactMatch	FB:FBgn0000008	semapv:UnspecifiedMatching
UniProtKB:P12345	skos:closeMatch	HGNC:123	semapv:UnspecifiedMatching
UBERON:0001977	skos:broadMatch	LOINC:LP7567-3	semapv:UnspecifiedMatching
"""

MIXED_PREDICATE_EDGES = """id	subject	predicate	object	category
e1	FB:FBgn0000008	biolink:related_to	MONDO:0000001	biolink:Association
e2	HGNC:123	biolink:related_to	MONDO:0000001	biolink:Association
e3	LOINC:LP7567-3	biolink:related_to	MONDO:0000001	biolink:Association
"""


def _write_edges_database(temp_dir: Path, name: str, edges_content: str) -> Path:
    """Create a DuckDB database with an edges table loaded from TSV content."""
    edges_file = temp_dir / f"{name}.edges.tsv"
    edges_file.write_text(edges_content)

    db_file = temp_dir / f"{name}.duckdb"
    with GraphDatabase(db_file) as db:
        db.conn.execute(
            "CREATE TABLE edges AS SELECT * FROM read_csv(?, delim='\t', header=true, all_varchar=true)",
            [str(edges_file)],
        )
    return db_file


def _subjects_by_id(db_file: Path) -> dict[str, str]:
    with GraphDatabase(db_file) as db:
        return dict(db.conn.execute("SELECT id, subject FROM edges").fetchall())


@pytest.fixture
def mixed_predicate_sssom_file(temp_dir):
    """SSSOM file mixing exactMatch, closeMatch and broadMatch rows."""
    sssom_file = temp_dir / "mixed_predicates.sssom.tsv"
    sssom_file.write_text(MIXED_PREDICATE_SSSOM)
    return sssom_file


@pytest.fixture
def no_predicate_column_sssom_file(temp_dir):
    """SSSOM file that omits the optional predicate_id column entirely."""
    sssom_content = """# curie_map:
#   semapv: https://w3id.org/semapv/vocab/
subject_id	object_id	mapping_justification
NCBIGene:43852	FB:FBgn0000008	semapv:UnspecifiedMatching
UniProtKB:P12345	HGNC:123	semapv:UnspecifiedMatching
"""
    sssom_file = temp_dir / "no_predicate_column.sssom.tsv"
    sssom_file.write_text(sssom_content)
    return sssom_file


def test_normalize_default_applies_every_predicate(temp_dir, mixed_predicate_sssom_file):
    """Without use_match, behaviour is unchanged: every mapping row is applied as an identity."""
    db_file = _write_edges_database(temp_dir, "default_predicates", MIXED_PREDICATE_EDGES)

    config = NormalizeConfig(
        database_path=db_file,
        mapping_files=prepare_mapping_file_specs_from_paths([mixed_predicate_sssom_file]),
        quiet=True,
        show_progress=False,
    )
    result = normalize_graph(config)

    assert result.success is True
    assert result.edges_normalized == 3

    subjects = _subjects_by_id(db_file)
    assert subjects["e1"] == "NCBIGene:43852"  # exactMatch
    assert subjects["e2"] == "UniProtKB:P12345"  # closeMatch, applied as today
    assert subjects["e3"] == "UBERON:0001977"  # broadMatch, applied as today


def test_normalize_use_match_exact_only(temp_dir, mixed_predicate_sssom_file):
    """use_match=['skos:exactMatch'] applies only the exact rows."""
    db_file = _write_edges_database(temp_dir, "exact_only", MIXED_PREDICATE_EDGES)

    config = NormalizeConfig(
        database_path=db_file,
        mapping_files=prepare_mapping_file_specs_from_paths([mixed_predicate_sssom_file]),
        use_match=["skos:exactMatch"],
        quiet=True,
        show_progress=False,
    )
    result = normalize_graph(config)

    assert result.success is True
    assert result.edges_normalized == 1

    subjects = _subjects_by_id(db_file)
    assert subjects["e1"] == "NCBIGene:43852"
    assert subjects["e2"] == "HGNC:123"  # closeMatch not applied
    assert subjects["e3"] == "LOINC:LP7567-3"  # broadMatch not applied

    # Only the exact mapping survives into the mappings table
    with GraphDatabase(db_file) as db:
        predicates = [row[0] for row in db.conn.execute("SELECT predicate_id FROM mappings").fetchall()]
        assert predicates == ["skos:exactMatch"]


def test_normalize_use_match_multiple_predicates(temp_dir, mixed_predicate_sssom_file):
    """Several predicates can be opted into at once."""
    db_file = _write_edges_database(temp_dir, "exact_and_close", MIXED_PREDICATE_EDGES)

    config = NormalizeConfig(
        database_path=db_file,
        mapping_files=prepare_mapping_file_specs_from_paths([mixed_predicate_sssom_file]),
        use_match=["skos:exactMatch", "skos:closeMatch"],
        quiet=True,
        show_progress=False,
    )
    result = normalize_graph(config)

    assert result.success is True
    assert result.edges_normalized == 2

    subjects = _subjects_by_id(db_file)
    assert subjects["e1"] == "NCBIGene:43852"
    assert subjects["e2"] == "UniProtKB:P12345"
    assert subjects["e3"] == "LOINC:LP7567-3"  # broadMatch still not applied


def test_non_exact_predicates_warn_when_use_match_unset(temp_dir, mixed_predicate_sssom_file, caplog):
    """Mixed input with no use_match warns and names the per-predicate counts."""
    db_file = _write_edges_database(temp_dir, "warning_fires", MIXED_PREDICATE_EDGES)

    config = NormalizeConfig(
        database_path=db_file,
        mapping_files=prepare_mapping_file_specs_from_paths([mixed_predicate_sssom_file]),
        quiet=True,
        show_progress=False,
    )
    result = normalize_graph(config)

    assert result.success is True

    non_exact_warnings = [w for w in result.warnings if "non-exact SSSOM mappings" in w]
    assert len(non_exact_warnings) == 1

    warning = non_exact_warnings[0]
    assert "Applying 2 non-exact SSSOM mappings" in warning  # the exactMatch row is not counted
    assert "skos:broadMatch: 1" in warning
    assert "skos:closeMatch: 1" in warning
    assert "skos:exactMatch: " not in warning
    assert "use_match" in warning

    # The same message reaches the logger
    assert any("non-exact SSSOM mappings" in record.message for record in caplog.records)


def test_no_non_exact_warning_for_all_exact_mappings(test_database, sample_sssom_file):
    """An all-exactMatch mapping set produces no predicate warning."""
    config = NormalizeConfig(
        database_path=test_database,
        mapping_files=prepare_mapping_file_specs_from_paths([sample_sssom_file]),
        quiet=True,
        show_progress=False,
    )
    result = normalize_graph(config)

    assert result.success is True
    assert [w for w in result.warnings if "non-exact SSSOM mappings" in w] == []


def test_no_non_exact_warning_when_use_match_set(temp_dir, mixed_predicate_sssom_file):
    """Opting in silences the warning - the caller has made the choice explicit."""
    db_file = _write_edges_database(temp_dir, "warning_silenced", MIXED_PREDICATE_EDGES)

    config = NormalizeConfig(
        database_path=db_file,
        mapping_files=prepare_mapping_file_specs_from_paths([mixed_predicate_sssom_file]),
        use_match=["skos:exactMatch"],
        quiet=True,
        show_progress=False,
    )
    result = normalize_graph(config)

    assert result.success is True
    assert [w for w in result.warnings if "non-exact SSSOM mappings" in w] == []


def test_mapping_file_without_predicate_id_column(temp_dir, no_predicate_column_sssom_file):
    """predicate_id is optional in SSSOM - such files must keep working unchanged."""
    db_file = _write_edges_database(temp_dir, "no_predicate_column", MIXED_PREDICATE_EDGES)

    config = NormalizeConfig(
        database_path=db_file,
        mapping_files=prepare_mapping_file_specs_from_paths([no_predicate_column_sssom_file]),
        quiet=True,
        show_progress=False,
    )
    result = normalize_graph(config)

    assert result.success is True
    assert result.edges_normalized == 2
    assert [w for w in result.warnings if "non-exact SSSOM mappings" in w] == []

    subjects = _subjects_by_id(db_file)
    assert subjects["e1"] == "NCBIGene:43852"
    assert subjects["e2"] == "UniProtKB:P12345"


def test_use_match_with_missing_predicate_id_column_keeps_all_mappings(
    temp_dir, no_predicate_column_sssom_file, caplog
):
    """use_match cannot be enforced without predicate_id, so nothing is dropped."""
    db_file = _write_edges_database(temp_dir, "no_predicate_column_use_match", MIXED_PREDICATE_EDGES)

    config = NormalizeConfig(
        database_path=db_file,
        mapping_files=prepare_mapping_file_specs_from_paths([no_predicate_column_sssom_file]),
        use_match=["skos:exactMatch"],
        quiet=True,
        show_progress=False,
    )
    result = normalize_graph(config)

    assert result.success is True
    assert result.edges_normalized == 2
    assert any("no predicate_id column" in record.message for record in caplog.records)


def test_use_match_keeps_rows_from_files_without_predicate_id(
    temp_dir, mixed_predicate_sssom_file, no_predicate_column_sssom_file
):
    """Mixing a file with predicate_id and one without must not drop the latter's rows."""
    db_file = _write_edges_database(temp_dir, "mixed_files", MIXED_PREDICATE_EDGES)

    # The predicate-less file maps LOINC:LP7567-3, which the mixed file only maps via broadMatch
    extra = temp_dir / "extra_no_predicate.sssom.tsv"
    extra.write_text("subject_id\tobject_id\nLOINC:9999-9\tLOINC:LP7567-3\n")

    config = NormalizeConfig(
        database_path=db_file,
        mapping_files=prepare_mapping_file_specs_from_paths([mixed_predicate_sssom_file, extra]),
        use_match=["skos:exactMatch"],
        quiet=True,
        show_progress=False,
    )
    result = normalize_graph(config)

    assert result.success is True

    subjects = _subjects_by_id(db_file)
    assert subjects["e1"] == "NCBIGene:43852"  # exactMatch applied
    assert subjects["e2"] == "HGNC:123"  # closeMatch filtered out
    assert subjects["e3"] == "LOINC:9999-9"  # NULL predicate_id row retained


def test_use_match_empty_list_is_treated_as_unset(test_database, sample_sssom_file):
    """An empty use_match must not be read as 'keep nothing'."""
    config = NormalizeConfig(
        database_path=test_database,
        mapping_files=prepare_mapping_file_specs_from_paths([sample_sssom_file]),
        use_match=[],
        quiet=True,
        show_progress=False,
    )

    assert config.use_match is None

    result = normalize_graph(config)
    assert result.success is True
    assert result.edges_normalized > 0


def test_use_match_typo_warns_instead_of_failing_silently(temp_dir, mixed_predicate_sssom_file):
    """A use_match predicate that matches nothing (e.g. wrong case) is surfaced as a warning."""
    db_file = _write_edges_database(temp_dir, "typo", MIXED_PREDICATE_EDGES)

    config = NormalizeConfig(
        database_path=db_file,
        mapping_files=prepare_mapping_file_specs_from_paths([mixed_predicate_sssom_file]),
        use_match=["skos:exactmatch"],
        quiet=True,
        show_progress=False,
    )
    result = normalize_graph(config)

    assert result.success is True
    assert result.edges_normalized == 0
    assert any("['skos:exactmatch'] matched no SSSOM mappings" in w for w in result.warnings)
    assert any("removed all 3 SSSOM mappings" in w for w in result.warnings)


def test_use_match_partially_unmatched_predicate_warns(temp_dir, mixed_predicate_sssom_file):
    """One good and one unmatched predicate: the good one applies, the bad one is named."""
    db_file = _write_edges_database(temp_dir, "partial_typo", MIXED_PREDICATE_EDGES)

    config = NormalizeConfig(
        database_path=db_file,
        mapping_files=prepare_mapping_file_specs_from_paths([mixed_predicate_sssom_file]),
        use_match=["skos:exactMatch", "skos:closematch"],
        quiet=True,
        show_progress=False,
    )
    result = normalize_graph(config)

    assert result.edges_normalized == 1
    assert any("['skos:closematch'] matched no SSSOM mappings" in w for w in result.warnings)
    assert not any("removed all" in w for w in result.warnings)


def test_no_use_match_warnings_when_all_predicates_match(temp_dir, mixed_predicate_sssom_file):
    db_file = _write_edges_database(temp_dir, "all_match", MIXED_PREDICATE_EDGES)

    config = NormalizeConfig(
        database_path=db_file,
        mapping_files=prepare_mapping_file_specs_from_paths([mixed_predicate_sssom_file]),
        use_match=["skos:exactMatch"],
        quiet=True,
        show_progress=False,
    )
    result = normalize_graph(config)

    assert result.warnings == []


@pytest.mark.parametrize("bad_value", ["exactMatch", "exact"])
def test_use_match_rejects_values_without_prefix(test_database, sample_sssom_file, bad_value):
    """Bare names can never match a predicate_id CURIE, so they are rejected up front."""
    with pytest.raises(ValueError, match="predicate CURIEs"):
        NormalizeConfig(
            database_path=test_database,
            mapping_files=prepare_mapping_file_specs_from_paths([sample_sssom_file]),
            use_match=[bad_value],
        )


def test_use_match_iri_entries_are_contracted(test_database, sample_sssom_file):
    config = NormalizeConfig(
        database_path=test_database,
        mapping_files=prepare_mapping_file_specs_from_paths([sample_sssom_file]),
        use_match=["http://www.w3.org/2004/02/skos/core#exactMatch", "skos:exactMatch"],
    )
    assert config.use_match == ["skos:exactMatch"]


IRI_PREDICATE_SSSOM = """subject_id	predicate_id	object_id
NCBIGene:43852	http://www.w3.org/2004/02/skos/core#exactMatch	FB:FBgn0000008
UniProtKB:P12345	http://www.w3.org/2004/02/skos/core#closeMatch	HGNC:123
"""


def test_iri_form_predicates_match_curie_use_match(temp_dir):
    """predicate_id written as a full IRI is compared as its CURIE."""
    db_file = _write_edges_database(temp_dir, "iri_predicates", MIXED_PREDICATE_EDGES)
    sssom = temp_dir / "iri.sssom.tsv"
    sssom.write_text(IRI_PREDICATE_SSSOM)

    config = NormalizeConfig(
        database_path=db_file,
        mapping_files=prepare_mapping_file_specs_from_paths([sssom]),
        use_match=["skos:exactMatch"],
        quiet=True,
        show_progress=False,
    )
    result = normalize_graph(config)

    assert result.edges_normalized == 1
    assert result.warnings == []
    subjects = _subjects_by_id(db_file)
    assert subjects["e1"] == "NCBIGene:43852"
    assert subjects["e2"] == "HGNC:123"


def test_iri_form_exact_match_not_counted_as_non_exact(temp_dir):
    db_file = _write_edges_database(temp_dir, "iri_warning", MIXED_PREDICATE_EDGES)
    sssom = temp_dir / "iri.sssom.tsv"
    sssom.write_text(IRI_PREDICATE_SSSOM)

    config = NormalizeConfig(
        database_path=db_file,
        mapping_files=prepare_mapping_file_specs_from_paths([sssom]),
        quiet=True,
        show_progress=False,
    )
    result = normalize_graph(config)

    [warning] = [w for w in result.warnings if "non-exact SSSOM mappings" in w]
    assert "Applying 1 non-exact SSSOM mappings" in warning
    assert "skos:closeMatch: 1" in warning
    assert "exactMatch" not in warning.split("(")[1].split(")")[0]


BLANK_PREDICATE_SSSOM = """subject_id	predicate_id	object_id
NCBIGene:43852	skos:exactMatch	FB:FBgn0000008
UniProtKB:P12345		HGNC:123
"""


@pytest.mark.parametrize("use_match", [["skos:exactMatch"], None], ids=["use_match_set", "use_match_unset"])
def test_blank_predicate_in_file_with_column_raises(temp_dir, use_match):
    """A blank predicate_id in a file that has the column is malformed SSSOM and raises."""
    db_file = _write_edges_database(temp_dir, "blank_predicate", MIXED_PREDICATE_EDGES)
    sssom = temp_dir / "blank.sssom.tsv"
    sssom.write_text(BLANK_PREDICATE_SSSOM)

    config = NormalizeConfig(
        database_path=db_file,
        mapping_files=prepare_mapping_file_specs_from_paths([sssom]),
        use_match=use_match,
        quiet=True,
        show_progress=False,
    )
    with pytest.raises(MalformedMappingError) as excinfo:
        normalize_graph(config)

    error = str(excinfo.value)
    assert "Malformed SSSOM file" in error
    assert "blank.sssom.tsv" in error
    assert "1 row(s) have a blank predicate_id" in error
    assert "UniProtKB:P12345 -> HGNC:123" in error

    # Edges are left untouched
    assert _subjects_by_id(db_file)["e1"] == "FB:FBgn0000008"


def test_blank_predicate_error_counts_and_limits_examples(temp_dir):
    db_file = _write_edges_database(temp_dir, "many_blanks", MIXED_PREDICATE_EDGES)
    sssom = temp_dir / "many_blanks.sssom.tsv"
    sssom.write_text(
        "subject_id\tpredicate_id\tobject_id\nA:1\t\tB:1\nA:2\t \tB:2\nA:3\t\tB:3\nA:4\tskos:exactMatch\tB:4\n"
    )

    config = NormalizeConfig(
        database_path=db_file,
        mapping_files=prepare_mapping_file_specs_from_paths([sssom]),
        quiet=True,
        show_progress=False,
    )
    with pytest.raises(MalformedMappingError) as excinfo:
        normalize_graph(config)

    error = str(excinfo.value)
    assert "3 row(s) have a blank predicate_id" in error
    assert "A:1 -> B:1" in error
    assert "A:2 -> B:2" in error
    assert "A:3" not in error  # at most two examples


def test_cli_normalize_exits_nonzero_on_malformed_mapping_file(temp_dir):
    from typer.testing import CliRunner

    from koza.main import typer_app

    db_file = _write_edges_database(temp_dir, "cli_blank", MIXED_PREDICATE_EDGES)
    sssom = temp_dir / "blank.sssom.tsv"
    sssom.write_text(BLANK_PREDICATE_SSSOM)

    result = CliRunner().invoke(typer_app, ["normalize", str(db_file), "-m", str(sssom), "-q"])

    assert result.exit_code != 0
    assert "Malformed SSSOM file" in result.output


def test_cli_normalize_exits_nonzero_when_operation_fails(temp_dir, sample_sssom_file):
    """A failed NormalizeResult (here: no nodes/edges tables) must not exit 0."""
    from typer.testing import CliRunner

    from koza.main import typer_app

    db_file = temp_dir / "empty_cli.duckdb"
    with GraphDatabase(db_file):
        pass

    result = CliRunner().invoke(typer_app, ["normalize", str(db_file), "-m", str(sample_sssom_file), "-q"])

    assert result.exit_code != 0


def test_predicate_filter_runs_before_object_id_dedup(temp_dir):
    """
    One object_id with both a broadMatch and an exactMatch row: without a filter the dedup
    keeps the broad row (it sorts first by subject_id); with exact-only the exact row must win.
    """
    sssom_content = """subject_id	predicate_id	object_id
AAA:broader	skos:broadMatch	FB:FBgn0000008
ZZZ:exact	skos:exactMatch	FB:FBgn0000008
"""
    sssom = temp_dir / "dedup.sssom.tsv"
    sssom.write_text(sssom_content)

    default_db = _write_edges_database(temp_dir, "dedup_default", MIXED_PREDICATE_EDGES)
    normalize_graph(
        NormalizeConfig(
            database_path=default_db,
            mapping_files=prepare_mapping_file_specs_from_paths([sssom]),
            quiet=True,
            show_progress=False,
        )
    )
    assert _subjects_by_id(default_db)["e1"] == "AAA:broader"

    exact_db = _write_edges_database(temp_dir, "dedup_exact", MIXED_PREDICATE_EDGES)
    result = normalize_graph(
        NormalizeConfig(
            database_path=exact_db,
            mapping_files=prepare_mapping_file_specs_from_paths([sssom]),
            use_match=["skos:exactMatch"],
            quiet=True,
            show_progress=False,
        )
    )
    assert _subjects_by_id(exact_db)["e1"] == "ZZZ:exact"
    assert not any("duplicate mappings" in w for w in result.warnings)


if __name__ == "__main__":
    pytest.main([__file__])
