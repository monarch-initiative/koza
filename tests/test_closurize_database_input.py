import pytest
import tempfile
import duckdb
from pathlib import Path
from click.testing import CliRunner
from koza.graph_operations._closurize_engine import add_closure


def test_database_input_functionality():
    """Test that closurizer can read from an existing DuckDB database"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a working database with nodes and edges tables
        working_db_path = temp_path / "working.duckdb"
        working_db = duckdb.connect(str(working_db_path))
        
        # Create test nodes table
        working_db.sql("""
        CREATE TABLE nodes (
            id VARCHAR,
            name VARCHAR,
            category VARCHAR,
            in_taxon VARCHAR,
            in_taxon_label VARCHAR
        )
        """)
        working_db.sql("""
        INSERT INTO nodes VALUES
            ('X:1', 'x1', 'Gene', 'NCBITaxon:9606', 'human'),
            ('X:2', 'x2', 'Gene', 'NCBITaxon:9606', 'human'),
            ('Y:1', 'y1', 'Disease', NULL, NULL)
        """)
        
        # Create test edges table  
        working_db.sql("""
        CREATE TABLE edges (
            subject VARCHAR,
            predicate VARCHAR,
            object VARCHAR,
            has_evidence VARCHAR,
            publications VARCHAR,
            negated BOOLEAN
        )
        """)
        working_db.sql("""
        INSERT INTO edges VALUES
            ('X:1', 'biolink:related_to', 'Y:1', 'ECO:1|ECO:2', 'PMID:1|PMID:2', false),
            ('X:2', 'biolink:related_to', 'Y:1', 'ECO:1', 'PMID:1', false)
        """)
        
        working_db.close()
        
        # Create closure file
        closure_content = """X:1	rdfs:subClassOf	X:2
X:2	rdfs:subClassOf	Y:1"""
        closure_file = temp_path / "closure.tsv"
        closure_file.write_text(closure_content)
        
        # Output files
        nodes_output = temp_path / "nodes_output.tsv"
        edges_output = temp_path / "edges_output.tsv"
        
        # Run closurizer with database input (no --kg means use existing database)
        add_closure(
            database_path=str(working_db_path),
            closure_file=str(closure_file),
            nodes_output_file=str(nodes_output),
            edges_output_file=str(edges_output),
            export_edges=True,
            export_nodes=True
        )
        
        # Verify output files were created
        assert nodes_output.exists()
        assert edges_output.exists()
        assert working_db_path.exists()
        
        # Verify TSV export contains pipe-delimited strings (this tests the core functionality)
        edges_output_content = edges_output.read_text()
        assert "ECO:1|ECO:2" in edges_output_content
        assert "PMID:1|PMID:2" in edges_output_content
        
        # Basic verification that processing occurred correctly
        nodes_output_content = nodes_output.read_text()
        assert "NCBITaxon:9606" in nodes_output_content
        assert "human" in nodes_output_content


def test_database_input_missing_tables():
    """Test error handling when database is missing required tables"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a database with only nodes table (missing edges)
        incomplete_db_path = temp_path / "incomplete.duckdb"
        incomplete_db = duckdb.connect(str(incomplete_db_path))
        
        # Create only nodes table
        incomplete_db.sql("""
        CREATE TABLE nodes (id VARCHAR, name VARCHAR, category VARCHAR)
        """)
        incomplete_db.sql("""
        INSERT INTO nodes VALUES ('X:1', 'x1', 'Gene')
        """)
        
        incomplete_db.close()
        
        # Create minimal closure file
        closure_file = temp_path / "closure.tsv"
        closure_file.write_text("X:1\trdfs:subClassOf\tX:1")
        
        # Output files
        nodes_output = temp_path / "nodes_output.tsv"
        edges_output = temp_path / "edges_output.tsv"
        
        # Run closurizer with incomplete database
        with pytest.raises(Exception):
            add_closure(
                database_path=str(incomplete_db_path),
                closure_file=str(closure_file),
                nodes_output_file=str(nodes_output),
                edges_output_file=str(edges_output)
            )


def test_missing_database_with_no_archive():
    """Test error handling when no kg_archive is provided and database doesn't exist."""
    with pytest.raises(ValueError, match="must be specified or database_path must exist"):
        add_closure(
            database_path="nonexistent.duckdb",
            closure_file="closure.tsv",
            nodes_output_file="nodes.tsv",
            edges_output_file="edges.tsv",
        )


def test_custom_database_path():
    """Test that custom database path is used correctly"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create working database  
        working_db_path = temp_path / "my-custom-database.duckdb"
        working_db = duckdb.connect(str(working_db_path))
        
        # Create minimal test data with required fields
        working_db.sql("""
        CREATE TABLE nodes (id VARCHAR, name VARCHAR, category VARCHAR, in_taxon VARCHAR, in_taxon_label VARCHAR)
        """)
        working_db.sql("""INSERT INTO nodes VALUES ('X:1', 'x1', 'Gene', 'NCBITaxon:9606', 'human')""")
        
        working_db.sql("""
        CREATE TABLE edges (subject VARCHAR, predicate VARCHAR, object VARCHAR, has_evidence VARCHAR, publications VARCHAR, negated BOOLEAN)
        """)
        working_db.sql("""INSERT INTO edges VALUES ('X:1', 'biolink:related_to', 'X:1', 'ECO:1', 'PMID:1', false)""")
        
        working_db.close()
        
        # Create closure file
        closure_file = temp_path / "closure.tsv"
        closure_file.write_text("X:1\trdfs:subClassOf\tX:1")
        
        # Output files
        nodes_output = temp_path / "nodes.tsv"
        edges_output = temp_path / "edges.tsv"
        
        # Run with custom database path
        add_closure(
            database_path=str(working_db_path),
            closure_file=str(closure_file),
            nodes_output_file=str(nodes_output),
            edges_output_file=str(edges_output),
            export_edges=True,
            export_nodes=True
        )
        assert working_db_path.exists(), "Custom database path should exist"


def test_descendant_fields_in_nodes_output():
    """Test that descendant fields (has_descendant, has_descendant_label, has_descendant_count) are properly added to nodes output"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create working database with hierarchical test data
        working_db_path = temp_path / "test.duckdb" 
        working_db = duckdb.connect(str(working_db_path))
        
        # Create nodes table with a simple hierarchy
        working_db.sql("""
        CREATE TABLE nodes (
            id VARCHAR,
            name VARCHAR,
            category VARCHAR,
            in_taxon VARCHAR,
            in_taxon_label VARCHAR
        )
        """)
        working_db.sql("""
        INSERT INTO nodes VALUES
            ('ROOT:1', 'root', 'biolink:NamedThing', NULL, NULL),
            ('CHILD:1', 'child1', 'biolink:Gene', 'NCBITaxon:9606', 'human'),
            ('CHILD:2', 'child2', 'biolink:Gene', 'NCBITaxon:9606', 'human'),
            ('GRANDCHILD:1', 'grandchild1', 'biolink:Gene', 'NCBITaxon:9606', 'human')
        """)
        
        # Create edges table
        working_db.sql("""
        CREATE TABLE edges (
            subject VARCHAR,
            predicate VARCHAR,
            object VARCHAR,
            has_evidence VARCHAR,
            publications VARCHAR,
            negated BOOLEAN
        )
        """)
        working_db.sql("""
        INSERT INTO edges VALUES
            ('ROOT:1', 'biolink:related_to', 'CHILD:1', 'ECO:1', 'PMID:1', false),
            ('CHILD:1', 'biolink:related_to', 'GRANDCHILD:1', 'ECO:2', 'PMID:2', false)
        """)
        
        working_db.close()
        
        # Create closure file with hierarchy: ROOT:1 -> CHILD:1 -> GRANDCHILD:1
        # Also add CHILD:2 as descendant of ROOT:1
        closure_content = """CHILD:1	rdfs:subClassOf	ROOT:1
CHILD:2	rdfs:subClassOf	ROOT:1
GRANDCHILD:1	rdfs:subClassOf	CHILD:1
GRANDCHILD:1	rdfs:subClassOf	ROOT:1"""
        closure_file = temp_path / "closure.tsv"
        closure_file.write_text(closure_content)
        
        # Output files
        nodes_output = temp_path / "nodes_output.tsv" 
        edges_output = temp_path / "edges_output.tsv"
        
        # Run closurizer
        add_closure(
            database_path=str(working_db_path),
            closure_file=str(closure_file),
            nodes_output_file=str(nodes_output),
            edges_output_file=str(edges_output),
            export_nodes=True,
            export_edges=True
        )
        
        # Verify output files were created
        assert nodes_output.exists()
        
        # Read and verify nodes output contains descendant fields
        nodes_content = nodes_output.read_text()
        
        # Check that header contains descendant columns
        lines = nodes_content.strip().split('\n')
        header = lines[0].split('\t')
        
        assert 'has_descendant' in header, f"Missing has_descendant column in header: {header}"
        assert 'has_descendant_label' in header, f"Missing has_descendant_label column in header: {header}"
        assert 'has_descendant_count' in header, f"Missing has_descendant_count column in header: {header}"
        
        # Check that ROOT:1 has descendants
        root_line = None
        for line in lines[1:]:  # Skip header
            fields = line.split('\t')
            if len(fields) > 0 and fields[0] == 'ROOT:1':  # Assuming id is first column
                root_line = line
                break
        
        assert root_line is not None, "ROOT:1 not found in nodes output"
        
        # ROOT:1 should have CHILD:1, CHILD:2, and GRANDCHILD:1 as descendants
        # Check that has_descendant_count > 0 for ROOT:1
        descendant_count_idx = header.index('has_descendant_count')
        root_fields = root_line.split('\t')
        descendant_count = int(root_fields[descendant_count_idx]) if len(root_fields) > descendant_count_idx and root_fields[descendant_count_idx].isdigit() else 0
        
        assert descendant_count > 0, f"ROOT:1 should have descendants, got count: {descendant_count}"
        
        # Check that has_descendant field contains descendant IDs (pipe-delimited)
        descendants_idx = header.index('has_descendant')
        if len(root_fields) > descendants_idx:
            descendants_field = root_fields[descendants_idx]
            # Should contain CHILD:1, CHILD:2, GRANDCHILD:1 in some form
            assert 'CHILD:1' in descendants_field or 'CHILD:2' in descendants_field or 'GRANDCHILD:1' in descendants_field, \
                f"ROOT:1 has_descendant field should contain descendant IDs, got: {descendants_field}"