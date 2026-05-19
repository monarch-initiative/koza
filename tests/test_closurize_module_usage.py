import pytest
import tempfile
import duckdb
import tarfile
from pathlib import Path
from koza.graph_operations._closurize_engine import add_closure


def test_module_usage_archive_input():
    """Test using add_closure as a module with archive input"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test TSV files
        nodes_content = """id	name	category	in_taxon	in_taxon_label
X:1	x1	Gene	NCBITaxon:9606	human
Y:1	y1	Disease		
"""
        
        edges_content = """subject	predicate	object	has_evidence	publications	negated
X:1	biolink:related_to	Y:1	ECO:1	PMID:1	False
"""
        
        # Create TSV files
        nodes_file = temp_path / "test_nodes.tsv"
        edges_file = temp_path / "test_edges.tsv"
        nodes_file.write_text(nodes_content)
        edges_file.write_text(edges_content)
        
        # Create tar.gz archive
        archive_path = temp_path / "test_kg.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(nodes_file, arcname="test_nodes.tsv")
            tar.add(edges_file, arcname="test_edges.tsv")
        
        # Create closure file
        closure_file = temp_path / "closure.tsv"
        closure_file.write_text("X:1\trdfs:subClassOf\tY:1")
        
        # Output files
        nodes_output = temp_path / "nodes_out.tsv"
        edges_output = temp_path / "edges_out.tsv"
        
        # Test module usage with archive input
        add_closure(
            closure_file=str(closure_file),
            nodes_output_file=str(nodes_output),
            edges_output_file=str(edges_output),
            kg_archive=str(archive_path),
            export_edges=True,
            export_nodes=True
        )
        
        # Verify outputs were created
        assert nodes_output.exists()
        assert edges_output.exists()
        
        # Verify content
        edges_content = edges_output.read_text()
        assert "X:1" in edges_content
        assert "Y:1" in edges_content


def test_module_usage_database_input():
    """Test using add_closure as a module with database input"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create working database
        db_path = temp_path / "working.duckdb"
        db = duckdb.connect(str(db_path))
        
        # Create test data
        db.sql("""
        CREATE TABLE nodes (
            id VARCHAR,
            name VARCHAR, 
            category VARCHAR,
            in_taxon VARCHAR,
            in_taxon_label VARCHAR
        )
        """)
        db.sql("""
        INSERT INTO nodes VALUES
            ('X:1', 'x1', 'Gene', 'NCBITaxon:9606', 'human'),
            ('Y:1', 'y1', 'Disease', NULL, NULL)
        """)
        
        db.sql("""
        CREATE TABLE edges (
            subject VARCHAR,
            predicate VARCHAR,
            object VARCHAR,
            has_evidence VARCHAR,
            publications VARCHAR,
            negated BOOLEAN
        )
        """)
        db.sql("""
        INSERT INTO edges VALUES
            ('X:1', 'biolink:related_to', 'Y:1', 'ECO:1', 'PMID:1', false)
        """)
        
        db.close()
        
        # Create closure file
        closure_file = temp_path / "closure.tsv"
        closure_file.write_text("X:1\trdfs:subClassOf\tY:1")
        
        # Output files  
        nodes_output = temp_path / "nodes_out.tsv"
        edges_output = temp_path / "edges_out.tsv"
        
        # Test module usage with database input (no kg_archive = use existing database)
        add_closure(
            closure_file=str(closure_file),
            nodes_output_file=str(nodes_output),
            edges_output_file=str(edges_output),
            database_path=str(db_path),
            export_edges=True,
            export_nodes=True
        )
        
        # Verify outputs were created
        assert nodes_output.exists()
        assert edges_output.exists()
        assert db_path.exists()
        
        # Verify content
        edges_content = edges_output.read_text()
        assert "X:1" in edges_content
        assert "Y:1" in edges_content


def test_module_parameter_validation():
    """Test parameter validation for module usage"""
    
    # Test missing kg_archive with non-existent database
    with pytest.raises(ValueError, match="Either kg_archive must be specified or database_path must exist"):
        add_closure(
            closure_file="test.tsv",
            nodes_output_file="nodes.tsv", 
            edges_output_file="edges.tsv",
            database_path="nonexistent.duckdb"
        )


def test_backward_compatibility_positional_args():
    """Test that old-style positional arguments still work (backward compatibility)"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create minimal test data with required fields
        nodes_content = "id\tname\tcategory\tin_taxon\tin_taxon_label\nX:1\tx1\tGene\tNCBITaxon:9606\thuman\n"
        edges_content = "subject\tpredicate\tobject\thas_evidence\tpublications\tnegated\nX:1\tbiolink:related_to\tX:1\tECO:1\tPMID:1\tFalse\n"
        
        nodes_file = temp_path / "test_nodes.tsv"
        edges_file = temp_path / "test_edges.tsv"
        nodes_file.write_text(nodes_content)
        edges_file.write_text(edges_content)
        
        archive_path = temp_path / "test_kg.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(nodes_file, arcname="test_nodes.tsv")
            tar.add(edges_file, arcname="test_edges.tsv")
        
        closure_file = temp_path / "closure.tsv"
        closure_file.write_text("X:1\trdfs:subClassOf\tX:1")
        
        nodes_output = temp_path / "nodes.tsv"
        edges_output = temp_path / "edges.tsv"
        
        # Test positional arguments (first 3 are required)
        add_closure(
            str(closure_file),      # closure_file
            str(nodes_output),      # nodes_output_file
            str(edges_output),      # edges_output_file
            str(archive_path),      # kg_archive
            export_edges=True,
            export_nodes=True
        )
        
        assert nodes_output.exists()
        assert edges_output.exists()