"""
Test suite for connectivity report graph operation.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import duckdb
import pytest
import yaml

from koza.model.graph_operations import ConnectivityReportConfig

# Check if ensmallen is available for integration tests
try:
    from ensmallen import Graph

    HAS_ENSMALLEN = True
except ImportError:
    HAS_ENSMALLEN = False

requires_ensmallen = pytest.mark.skipif(not HAS_ENSMALLEN, reason="ensmallen not installed (install koza[grape])")


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def synthetic_graph_db(temp_dir):
    """Create a small graph with known connectivity structure.

    Components (undirected):
      - Component 0 (LCC, 5 nodes): A-B-C-D-E (chain)
      - Component 1 (3 nodes): F-G-H (triangle)
      - Component 2 (singleton): I
      - Component 3 (singleton): J
    """
    db_path = temp_dir / "synthetic.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute("""
        CREATE TABLE nodes (id VARCHAR, category VARCHAR, name VARCHAR, provided_by VARCHAR);
        INSERT INTO nodes VALUES
            ('N:A', 'biolink:Gene', 'geneA', 'src1'),
            ('N:B', 'biolink:Gene', 'geneB', 'src1'),
            ('N:C', 'biolink:Disease', 'diseaseC', 'src2'),
            ('N:D', 'biolink:Gene', 'geneD', 'src1'),
            ('N:E', 'biolink:Gene', 'geneE', 'src1'),
            ('N:F', 'biolink:ChemicalEntity', 'chemF', 'src3'),
            ('N:G', 'biolink:ChemicalEntity', 'chemG', 'src3'),
            ('N:H', 'biolink:Disease', 'diseaseH', 'src2'),
            ('N:I', 'biolink:Gene', 'geneI', 'src1'),
            ('N:J', 'biolink:Disease', 'obsolete diseaseJ', 'src2');
    """)
    con.execute("""
        CREATE TABLE edges (
            subject VARCHAR, object VARCHAR, predicate VARCHAR,
            primary_knowledge_source VARCHAR, provided_by VARCHAR
        );
        INSERT INTO edges VALUES
            ('N:A', 'N:B', 'biolink:related_to', 'ks1', 'src1'),
            ('N:B', 'N:C', 'biolink:causes', 'ks1', 'src2'),
            ('N:C', 'N:D', 'biolink:related_to', 'ks2', 'src1'),
            ('N:D', 'N:E', 'biolink:related_to', 'ks1', 'src1'),
            ('N:F', 'N:G', 'biolink:interacts_with', 'ks3', 'src3'),
            ('N:G', 'N:H', 'biolink:related_to', 'ks2', 'src3'),
            ('N:H', 'N:F', 'biolink:causes', 'ks3', 'src2');
    """)
    con.close()
    return db_path


@pytest.fixture
def minimal_graph_db(temp_dir):
    """Create a graph with only the minimal required columns (id, subject, object)."""
    db_path = temp_dir / "minimal.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute("""
        CREATE TABLE nodes (id VARCHAR);
        INSERT INTO nodes VALUES ('A'), ('B'), ('C'), ('D');
    """)
    con.execute("""
        CREATE TABLE edges (subject VARCHAR, object VARCHAR);
        INSERT INTO edges VALUES ('A', 'B'), ('C', 'D');
    """)
    con.close()
    return db_path


# ---------------------------------------------------------------------------
# Unit tests (always run, no ensmallen needed)
# ---------------------------------------------------------------------------


class TestSizeBucket:
    """Test the _size_bucket pure function."""

    def test_lcc(self):
        from koza.graph_operations.connectivity import _size_bucket

        assert _size_bucket(1000, 1000) == "LCC"

    def test_large_component(self):
        from koza.graph_operations.connectivity import _size_bucket

        assert _size_bucket(500, 1000) == "100+"
        assert _size_bucket(100, 1000) == "100+"

    def test_medium_component(self):
        from koza.graph_operations.connectivity import _size_bucket

        assert _size_bucket(99, 1000) == "10-99"
        assert _size_bucket(10, 1000) == "10-99"

    def test_small_component(self):
        from koza.graph_operations.connectivity import _size_bucket

        assert _size_bucket(9, 1000) == "2-9"
        assert _size_bucket(2, 1000) == "2-9"

    def test_isolated(self):
        from koza.graph_operations.connectivity import _size_bucket

        assert _size_bucket(1, 1000) == "Isolated"


class TestConnectivityReportConfig:
    """Test Pydantic config validation."""

    def test_missing_database(self, temp_dir):
        with pytest.raises(ValueError, match="Database file not found"):
            ConnectivityReportConfig(database_path=temp_dir / "nonexistent.duckdb")

    def test_valid_config(self, synthetic_graph_db):
        config = ConnectivityReportConfig(database_path=synthetic_graph_db)
        assert config.directed is False
        assert config.node_name_column == "id"
        assert config.edge_src_column == "subject"

    def test_custom_columns(self, synthetic_graph_db):
        config = ConnectivityReportConfig(
            database_path=synthetic_graph_db,
            node_type_column=None,
            edge_type_column=None,
        )
        assert config.node_type_column is None
        assert config.edge_type_column is None


# ---------------------------------------------------------------------------
# Integration tests (require ensmallen)
# ---------------------------------------------------------------------------


@requires_ensmallen
class TestGenerateConnectivityReport:
    """Integration tests for the full connectivity report pipeline."""

    def test_basic_report(self, synthetic_graph_db):
        from koza.graph_operations.connectivity import generate_connectivity_report

        config = ConnectivityReportConfig(database_path=synthetic_graph_db, quiet=True)
        result = generate_connectivity_report(config)

        assert result.summary.num_nodes == 10
        assert result.summary.num_components == 4
        assert result.summary.lcc_size == 5
        assert result.summary.num_singletons == 2
        assert result.summary.num_non_singleton_components == 2
        assert result.summary.nodes_outside_lcc == 5
        assert result.computation_seconds >= 0
        assert result.total_time_seconds > 0

    def test_lcc_fraction(self, synthetic_graph_db):
        from koza.graph_operations.connectivity import generate_connectivity_report

        config = ConnectivityReportConfig(database_path=synthetic_graph_db, quiet=True)
        result = generate_connectivity_report(config)

        assert result.summary.lcc_fraction == pytest.approx(0.5, abs=0.01)

    def test_size_distribution(self, synthetic_graph_db):
        from koza.graph_operations.connectivity import generate_connectivity_report

        config = ConnectivityReportConfig(database_path=synthetic_graph_db, quiet=True)
        result = generate_connectivity_report(config)

        buckets = {d.bucket: d for d in result.summary.size_distribution}
        assert "LCC" in buckets
        assert buckets["LCC"].num_components == 1
        assert buckets["LCC"].total_nodes == 5
        assert "2-9" in buckets
        assert buckets["2-9"].num_components == 1
        assert buckets["2-9"].total_nodes == 3
        assert "Isolated" in buckets
        assert buckets["Isolated"].num_components == 2
        assert buckets["Isolated"].total_nodes == 2

    def test_deprecated_detection(self, synthetic_graph_db):
        from koza.graph_operations.connectivity import generate_connectivity_report

        config = ConnectivityReportConfig(database_path=synthetic_graph_db, quiet=True)
        result = generate_connectivity_report(config)

        # Node J has name "obsolete diseaseJ"
        assert result.summary.total_deprecated == 1

    def test_parquet_output(self, synthetic_graph_db, temp_dir):
        from koza.graph_operations.connectivity import generate_connectivity_report

        output_dir = temp_dir / "cc_output"
        config = ConnectivityReportConfig(
            database_path=synthetic_graph_db,
            output_dir=output_dir,
            quiet=True,
        )
        result = generate_connectivity_report(config)

        assert "cc_nodes" in result.parquet_files
        assert "cc_components" in result.parquet_files
        assert "cc_component_sources" in result.parquet_files

        for name, path in result.parquet_files.items():
            assert path.exists(), f"{name} parquet file should exist"

        # Verify we can read them back
        import pandas as pd

        cc_nodes = pd.read_parquet(result.parquet_files["cc_nodes"])
        assert len(cc_nodes) == 10
        assert "node_id" in cc_nodes.columns
        assert "component_id" in cc_nodes.columns

        cc_components = pd.read_parquet(result.parquet_files["cc_components"])
        assert len(cc_components) == 4

        cc_sources = pd.read_parquet(result.parquet_files["cc_component_sources"])
        assert len(cc_sources) > 0
        assert "edge_count" in cc_sources.columns

    def test_yaml_output(self, synthetic_graph_db, temp_dir):
        from koza.graph_operations.connectivity import generate_connectivity_report

        yaml_path = temp_dir / "summary.yaml"
        config = ConnectivityReportConfig(
            database_path=synthetic_graph_db,
            output_file=yaml_path,
            quiet=True,
        )
        result = generate_connectivity_report(config)

        assert yaml_path.exists()
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        assert data["num_components"] == 4
        assert data["lcc_size"] == 5
        assert data["graph_name"] == "KnowledgeGraph"

    def test_minimal_schema(self, minimal_graph_db):
        """Test with a database that has only id/subject/object columns."""
        from koza.graph_operations.connectivity import generate_connectivity_report

        config = ConnectivityReportConfig(
            database_path=minimal_graph_db,
            node_type_column=None,
            edge_type_column=None,
            quiet=True,
        )
        result = generate_connectivity_report(config)

        assert result.summary.num_nodes == 4
        assert result.summary.num_components == 2
        assert result.summary.lcc_size == 2

    def test_top_minor_components(self, synthetic_graph_db):
        from koza.graph_operations.connectivity import generate_connectivity_report

        config = ConnectivityReportConfig(database_path=synthetic_graph_db, quiet=True)
        result = generate_connectivity_report(config)

        # Should have up to 3 minor components (component 1 with 3 nodes, plus 2 singletons)
        assert len(result.summary.top_minor_components) >= 1
        top = result.summary.top_minor_components[0]
        assert top.component_size == 3
        assert len(top.sample_node_ids) > 0

    def test_console_output(self, synthetic_graph_db, capsys):
        """Verify console output is produced when quiet=False."""
        from koza.graph_operations.connectivity import generate_connectivity_report

        config = ConnectivityReportConfig(database_path=synthetic_graph_db, quiet=False)
        generate_connectivity_report(config)

        captured = capsys.readouterr()
        assert "CONNECTED COMPONENT REPORT" in captured.out
        assert "LCC size:" in captured.out

    def test_quiet_mode(self, synthetic_graph_db, capsys):
        """Verify no console output when quiet=True."""
        from koza.graph_operations.connectivity import generate_connectivity_report

        config = ConnectivityReportConfig(database_path=synthetic_graph_db, quiet=True)
        generate_connectivity_report(config)

        captured = capsys.readouterr()
        assert captured.out == ""


class TestMissingEnsmallen:
    """Test behavior when ensmallen is not installed."""

    def test_import_error_message(self, synthetic_graph_db):
        from koza.graph_operations.connectivity import generate_connectivity_report

        config = ConnectivityReportConfig(database_path=synthetic_graph_db, quiet=True)

        with patch("koza.graph_operations.connectivity._check_ensmallen_available", return_value=False):
            with pytest.raises(ImportError, match="koza\\[grape\\]"):
                generate_connectivity_report(config)
