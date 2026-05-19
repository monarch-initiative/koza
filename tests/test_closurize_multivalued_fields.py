import pytest
import tempfile
import duckdb
from pathlib import Path
from koza.graph_operations._closurize_engine import add_closure


def test_multivalued_edges_basic():
    """Test basic multivalued field handling in edges"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test database with multivalued fields
        db_path = temp_path / "test.duckdb"
        db = duckdb.connect(str(db_path))
        
        # Create nodes table
        db.sql("""
        CREATE TABLE nodes (
            id VARCHAR,
            name VARCHAR,
            category VARCHAR
        )
        """)
        db.sql("""
        INSERT INTO nodes VALUES
            ('GENE:1', 'gene1', 'biolink:Gene'),
            ('DISEASE:1', 'disease1', 'biolink:Disease'),
            ('QUAL:1', 'qualifier1', 'biolink:Qualifier'),
            ('QUAL:2', 'qualifier2', 'biolink:Qualifier')
        """)
        
        # Create edges table with multivalued qualifiers field
        db.sql("""
        CREATE TABLE edges (
            subject VARCHAR,
            predicate VARCHAR,
            object VARCHAR,
            qualifiers VARCHAR,
            has_evidence VARCHAR
        )
        """)
        db.sql("""
        INSERT INTO edges VALUES
            ('GENE:1', 'biolink:related_to', 'DISEASE:1', 'QUAL:1|QUAL:2', 'ECO:1|ECO:2'),
            ('GENE:1', 'biolink:associated_with', 'DISEASE:1', 'QUAL:1', 'ECO:1')
        """)
        
        db.close()
        
        # Create closure file
        closure_file = temp_path / "closure.tsv"
        closure_file.write_text("GENE:1\trdfs:subClassOf\tGENE:1\n")
        
        # Output files
        nodes_output = temp_path / "nodes.tsv"
        edges_output = temp_path / "edges.tsv"
        
        # Test with multivalued fields
        add_closure(
            closure_file=str(closure_file),
            nodes_output_file=str(nodes_output),
            edges_output_file=str(edges_output),
            database_path=str(db_path),
            edge_fields=['subject', 'object'],
            edge_fields_to_label=['qualifiers'],
            multivalued_fields=['qualifiers', 'has_evidence'],
            export_edges=True,
            export_nodes=True
        )
        
        # Verify output files exist
        assert edges_output.exists()
        assert nodes_output.exists()
        
        # Verify TSV content contains pipe-delimited values
        edges_content = edges_output.read_text()
        assert "QUAL:1|QUAL:2" in edges_content
        assert "ECO:1|ECO:2" in edges_content


def test_multivalued_single_value():
    """Test multivalued field handling with single values (no pipes)"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        db_path = temp_path / "test.duckdb"
        db = duckdb.connect(str(db_path))
        
        # Create test data with single values in multivalued fields
        db.sql("""
        CREATE TABLE nodes (
            id VARCHAR,
            name VARCHAR,
            category VARCHAR,
            in_taxon VARCHAR
        )
        """)
        db.sql("""
        INSERT INTO nodes VALUES
            ('GENE:1', 'gene1', 'biolink:Gene', 'NCBITaxon:9606')
        """)
        
        db.sql("""
        CREATE TABLE edges (
            subject VARCHAR,
            predicate VARCHAR,
            object VARCHAR,
            has_evidence VARCHAR
        )
        """)
        db.sql("""
        INSERT INTO edges VALUES
            ('GENE:1', 'biolink:related_to', 'GENE:1', 'ECO:1')
        """)
        
        db.close()
        
        closure_file = temp_path / "closure.tsv"
        closure_file.write_text("GENE:1\trdfs:subClassOf\tGENE:1\n")
        
        nodes_output = temp_path / "nodes.tsv"
        edges_output = temp_path / "edges.tsv"
        
        # Test with single values in multivalued fields
        add_closure(
            closure_file=str(closure_file),
            nodes_output_file=str(nodes_output),
            edges_output_file=str(edges_output),
            database_path=str(db_path),
            edge_fields=['subject', 'object'],
            multivalued_fields=['has_evidence', 'in_taxon'],
            export_edges=True,
            export_nodes=True
        )
        
        assert edges_output.exists()
        assert nodes_output.exists()
        
        # Single values should still appear correctly
        edges_content = edges_output.read_text()
        assert "ECO:1" in edges_content
        
        nodes_content = nodes_output.read_text()
        assert "NCBITaxon:9606" in nodes_content


def test_multivalued_null_values():
    """Test multivalued field handling with NULL values"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        db_path = temp_path / "test.duckdb"
        db = duckdb.connect(str(db_path))
        
        db.sql("""
        CREATE TABLE nodes (
            id VARCHAR,
            name VARCHAR,
            category VARCHAR,
            in_taxon VARCHAR
        )
        """)
        db.sql("""
        INSERT INTO nodes VALUES
            ('GENE:1', 'gene1', 'biolink:Gene', NULL)
        """)
        
        db.sql("""
        CREATE TABLE edges (
            subject VARCHAR,
            predicate VARCHAR,
            object VARCHAR,
            has_evidence VARCHAR
        )
        """)
        db.sql("""
        INSERT INTO edges VALUES
            ('GENE:1', 'biolink:related_to', 'GENE:1', NULL)
        """)
        
        db.close()
        
        closure_file = temp_path / "closure.tsv"
        closure_file.write_text("GENE:1\trdfs:subClassOf\tGENE:1\n")
        
        nodes_output = temp_path / "nodes.tsv"
        edges_output = temp_path / "edges.tsv"
        
        # Test with NULL values in multivalued fields
        add_closure(
            closure_file=str(closure_file),
            nodes_output_file=str(nodes_output),
            edges_output_file=str(edges_output),
            database_path=str(db_path),
            edge_fields=['subject', 'object'],
            multivalued_fields=['has_evidence', 'in_taxon'],
            export_edges=True,
            export_nodes=True
        )
        
        assert edges_output.exists()
        assert nodes_output.exists()


def test_multivalued_nodes_closure_fields():
    """Test that closure fields generated for nodes are properly handled as arrays"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        db_path = temp_path / "test.duckdb"
        db = duckdb.connect(str(db_path))
        
        # Create test data for node closure testing
        db.sql("""
        CREATE TABLE nodes (
            id VARCHAR,
            name VARCHAR,
            category VARCHAR
        )
        """)
        db.sql("""
        INSERT INTO nodes VALUES
            ('GENE:1', 'gene1', 'biolink:Gene'),
            ('PHENO:1', 'phenotype1', 'biolink:PhenotypicFeature'),
            ('PHENO:2', 'phenotype2', 'biolink:PhenotypicFeature')
        """)
        
        db.sql("""
        CREATE TABLE edges (
            subject VARCHAR,
            predicate VARCHAR,
            object VARCHAR
        )
        """)
        db.sql("""
        INSERT INTO edges VALUES
            ('GENE:1', 'biolink:has_phenotype', 'PHENO:1'),
            ('GENE:1', 'biolink:has_phenotype', 'PHENO:2')
        """)
        
        db.close()
        
        # Create closure with phenotype hierarchy
        closure_content = """PHENO:1\trdfs:subClassOf\tPHENO:1
PHENO:2\trdfs:subClassOf\tPHENO:2
PHENO:1\trdfs:subClassOf\tPHENO:PARENT
PHENO:2\trdfs:subClassOf\tPHENO:PARENT"""
        
        closure_file = temp_path / "closure.tsv"
        closure_file.write_text(closure_content)
        
        nodes_output = temp_path / "nodes.tsv"
        edges_output = temp_path / "edges.tsv"
        
        # Test node closure field generation
        add_closure(
            closure_file=str(closure_file),
            nodes_output_file=str(nodes_output),
            edges_output_file=str(edges_output),
            database_path=str(db_path),
            edge_fields=['subject', 'object'],
            node_fields=['has_phenotype'],
            multivalued_fields=[],
            export_nodes=True
        )
        
        assert nodes_output.exists()
        
        # Verify closure fields are properly generated and exported
        nodes_content = nodes_output.read_text()
        # Should contain has_phenotype closure information
        assert "PHENO:1" in nodes_content or "PHENO:2" in nodes_content


def test_multivalued_empty_fields():
    """Test multivalued field handling with empty string fields"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        db_path = temp_path / "test.duckdb"
        db = duckdb.connect(str(db_path))
        
        db.sql("""
        CREATE TABLE nodes (
            id VARCHAR,
            name VARCHAR,
            category VARCHAR,
            in_taxon VARCHAR
        )
        """)
        db.sql("""
        INSERT INTO nodes VALUES
            ('GENE:1', 'gene1', 'biolink:Gene', '')
        """)
        
        db.sql("""
        CREATE TABLE edges (
            subject VARCHAR,
            predicate VARCHAR,
            object VARCHAR,
            has_evidence VARCHAR
        )
        """)
        db.sql("""
        INSERT INTO edges VALUES
            ('GENE:1', 'biolink:related_to', 'GENE:1', '')
        """)
        
        db.close()
        
        closure_file = temp_path / "closure.tsv"
        closure_file.write_text("GENE:1\trdfs:subClassOf\tGENE:1\n")
        
        nodes_output = temp_path / "nodes.tsv"
        edges_output = temp_path / "edges.tsv"
        
        # Test with empty string values in multivalued fields
        add_closure(
            closure_file=str(closure_file),
            nodes_output_file=str(nodes_output),
            edges_output_file=str(edges_output),
            database_path=str(db_path),
            edge_fields=['subject', 'object'],
            multivalued_fields=['has_evidence', 'in_taxon'],
            export_edges=True,
            export_nodes=True
        )
        
        assert edges_output.exists()
        assert nodes_output.exists()