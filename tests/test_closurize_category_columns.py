import pytest
import tempfile
import duckdb
from pathlib import Path
from click.testing import CliRunner
from koza.graph_operations._closurize_engine import add_closure


def test_denormalized_edges_has_correct_category_columns():
    """Test that denormalized_edges table uses subject_category and object_category (not _1 suffix)

    This test verifies that when closurizer creates the denormalized_edges table,
    it properly names the category columns as 'subject_category' and 'object_category'
    rather than 'subject_category_1' and 'object_category_1'.

    The issue was that closurizer was creating denormalized_edges with the wrong column names,
    causing the categories to be NULL in the expected columns.
    """

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a working database with nodes and edges tables
        working_db_path = temp_path / "working.duckdb"
        working_db = duckdb.connect(str(working_db_path))

        # Create test nodes table with different categories
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
            ('GENE:1', 'gene1', 'biolink:Gene', 'NCBITaxon:9606', 'human'),
            ('GENE:2', 'gene2', 'biolink:Gene', 'NCBITaxon:9606', 'human'),
            ('DISEASE:1', 'disease1', 'biolink:Disease', NULL, NULL),
            ('PHENOTYPE:1', 'phenotype1', 'biolink:PhenotypicFeature', NULL, NULL)
        """)

        # Create test edges table with various category combinations
        # IMPORTANT: Include subject_category and object_category columns (which will be NULL/empty)
        # This reproduces the real-world scenario where edges table has these columns
        # but they're not populated, causing DuckDB to create _1 suffix columns
        working_db.sql("""
        CREATE TABLE edges (
            subject VARCHAR,
            predicate VARCHAR,
            object VARCHAR,
            subject_category VARCHAR,
            object_category VARCHAR,
            has_evidence VARCHAR,
            publications VARCHAR,
            negated BOOLEAN
        )
        """)
        working_db.sql("""
        INSERT INTO edges VALUES
            ('GENE:1', 'biolink:related_to', 'DISEASE:1', NULL, NULL, 'ECO:1', 'PMID:1', false),
            ('GENE:2', 'biolink:related_to', 'PHENOTYPE:1', NULL, NULL, 'ECO:2', 'PMID:2', false),
            ('DISEASE:1', 'biolink:has_phenotype', 'PHENOTYPE:1', NULL, NULL, 'ECO:3', 'PMID:3', false)
        """)

        working_db.close()

        # Create minimal closure file
        closure_content = """GENE:1	rdfs:subClassOf	GENE:2"""
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
            export_edges=True,
            export_nodes=True
        )

        # Now check the denormalized_edges table in the database
        check_db = duckdb.connect(str(working_db_path))

        # First, verify the table exists
        tables = check_db.sql("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        assert 'denormalized_edges' in table_names, f"denormalized_edges table not found. Available tables: {table_names}"

        # Get the column names from denormalized_edges
        columns = check_db.sql("PRAGMA table_info(denormalized_edges)").fetchall()
        column_names = [col[1] for col in columns]  # Column name is at index 1

        # CRITICAL: Check that subject_category and object_category exist (not _1 suffix)
        assert 'subject_category' in column_names, \
            f"subject_category column missing. Found columns: {column_names}"
        assert 'object_category' in column_names, \
            f"object_category column missing. Found columns: {column_names}"

        # Ensure no _1 suffix columns exist (that would indicate the bug)
        assert 'subject_category_1' not in column_names, \
            f"Bug detected: subject_category_1 exists, indicating column name collision"
        assert 'object_category_1' not in column_names, \
            f"Bug detected: object_category_1 exists, indicating column name collision"

        # Check that the categories are NOT in _1 columns (if they exist, they should not have the data)
        # If subject_category_1 exists, it should ideally not be there, but at minimum
        # subject_category should have the actual data

        # Verify that subject_category and object_category have actual data (not NULL)
        result = check_db.sql("""
            SELECT
                COUNT(*) as total,
                COUNT(subject_category) as subject_cat_count,
                COUNT(object_category) as object_cat_count
            FROM denormalized_edges
        """).fetchall()

        total = result[0][0]
        subject_cat_count = result[0][1]
        object_cat_count = result[0][2]

        assert total > 0, "denormalized_edges table is empty"
        assert subject_cat_count == total, \
            f"subject_category has NULLs: {subject_cat_count}/{total} rows have values"
        assert object_cat_count == total, \
            f"object_category has NULLs: {object_cat_count}/{total} rows have values"

        # Verify the actual category values are correct
        sample = check_db.sql("""
            SELECT subject, object, subject_category, object_category
            FROM denormalized_edges
            LIMIT 3
        """).fetchall()

        # Check that we have the expected categories
        categories = set()
        for row in sample:
            if row[2]:  # subject_category
                categories.add(row[2])
            if row[3]:  # object_category
                categories.add(row[3])
        expected_categories = {'biolink:Gene', 'biolink:Disease', 'biolink:PhenotypicFeature'}

        assert expected_categories.intersection(categories), \
            f"Expected to find categories from {expected_categories}, but got {categories}"

        check_db.close()
