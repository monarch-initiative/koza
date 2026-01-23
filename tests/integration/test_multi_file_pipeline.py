"""Integration tests for multi-file transforms and config-free transform mode."""

from pathlib import Path

from koza.model.formats import OutputFormat
from koza.model.koza import KozaConfig
from koza.model.reader import CSVReaderConfig, JSONReaderConfig, YAMLReaderConfig
from koza.model.transform import TransformConfig
from koza.model.writer import WriterConfig
from koza.runner import KozaRunner

# Default node and edge properties for writer output
DEFAULT_NODE_PROPERTIES = ["id", "category", "name"]
DEFAULT_EDGE_PROPERTIES = ["id", "subject", "predicate", "object", "category"]

# Transform code that works with biolink models
TRANSFORM_CODE = '''
import koza
from biolink_model.datamodel.pydanticmodel_v2 import NamedThing
from koza.model.graphs import KnowledgeGraph

@koza.transform_record()
def transform(koza, record):
    node = NamedThing(id=record["id"], name=record["name"], category=["biolink:NamedThing"])
    return KnowledgeGraph(nodes=[node])
'''


class TestMultiFilePipeline:
    """Test full pipeline with multiple input files."""

    def test_yaml_multiple_files(self, tmp_path):
        """Full pipeline: multiple YAML files yields records from all files."""
        # Create sample YAML files
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        for i in range(3):
            (data_dir / f"entity_{i}.yaml").write_text(f"id: entity_{i}\nname: Entity {i}\n")

        # Create a simple transform
        transform_file = tmp_path / "transform.py"
        transform_file.write_text(TRANSFORM_CODE)

        config = KozaConfig(
            name="yaml-multi-test",
            reader=YAMLReaderConfig(
                files=["data/entity_0.yaml", "data/entity_1.yaml", "data/entity_2.yaml"]
            ),
            transform=TransformConfig(code="transform.py"),
            writer=WriterConfig(format=OutputFormat.tsv, node_properties=DEFAULT_NODE_PROPERTIES),
        )

        output_dir = str(tmp_path / "output")
        runner = KozaRunner.from_config(
            config, base_directory=tmp_path, output_dir=output_dir, row_limit=0, show_progress=False
        )
        runner.run()

        # Verify output has records from all 3 files
        nodes_file = Path(output_dir) / "yaml-multi-test_nodes.tsv"
        assert nodes_file.exists()
        lines = nodes_file.read_text().strip().split("\n")
        # Header + 3 data rows
        assert len(lines) == 4

    def test_json_multiple_files(self, tmp_path):
        """Full pipeline: multiple JSON files yields records from all files."""
        # Create sample JSON files
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        for i in range(3):
            (data_dir / f"item_{i}.json").write_text(f'{{"id": "item_{i}", "name": "Item {i}"}}')

        # Create a simple transform
        transform_file = tmp_path / "transform.py"
        transform_file.write_text(TRANSFORM_CODE)

        config = KozaConfig(
            name="json-multi-test",
            reader=JSONReaderConfig(
                files=["data/item_0.json", "data/item_1.json", "data/item_2.json"]
            ),
            transform=TransformConfig(code="transform.py"),
            writer=WriterConfig(format=OutputFormat.tsv, node_properties=DEFAULT_NODE_PROPERTIES),
        )

        output_dir = str(tmp_path / "output")
        runner = KozaRunner.from_config(
            config, base_directory=tmp_path, output_dir=output_dir, row_limit=0, show_progress=False
        )
        runner.run()

        # Verify output has records from all 3 files
        nodes_file = Path(output_dir) / "json-multi-test_nodes.tsv"
        assert nodes_file.exists()
        lines = nodes_file.read_text().strip().split("\n")
        # Header + 3 data rows
        assert len(lines) == 4

    def test_csv_multiple_files(self, tmp_path):
        """Full pipeline: multiple TSV files combined."""
        # Create sample TSV files
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        for i in range(2):
            (data_dir / f"2024-0{i+1}.tsv").write_text(f"id\tname\nrow_{i}_1\tName {i} 1\nrow_{i}_2\tName {i} 2\n")

        # Create a simple transform
        transform_file = tmp_path / "transform.py"
        transform_file.write_text(TRANSFORM_CODE)

        config = KozaConfig(
            name="csv-multi-test",
            reader=CSVReaderConfig(files=["data/2024-01.tsv", "data/2024-02.tsv"], delimiter="\t"),
            transform=TransformConfig(code="transform.py"),
            writer=WriterConfig(format=OutputFormat.tsv, node_properties=DEFAULT_NODE_PROPERTIES),
        )

        output_dir = str(tmp_path / "output")
        runner = KozaRunner.from_config(
            config, base_directory=tmp_path, output_dir=output_dir, row_limit=0, show_progress=False
        )
        runner.run()

        # Verify output has records from both files (2 rows each)
        nodes_file = Path(output_dir) / "csv-multi-test_nodes.tsv"
        assert nodes_file.exists()
        lines = nodes_file.read_text().strip().split("\n")
        # Header + 4 data rows (2 per file)
        assert len(lines) == 5


class TestConfigFreeTransform:
    """Test config-free transform mode via CLI."""

    def test_config_free_yaml_pipeline(self, tmp_path):
        """Config-free mode processes multiple YAML files."""
        from typer.testing import CliRunner

        from koza.main import typer_app

        runner = CliRunner()

        # Create sample YAML files
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        for i in range(2):
            (data_dir / f"entity_{i}.yaml").write_text(f"id: entity_{i}\nname: Entity {i}\n")

        # Create a simple transform
        transform_file = tmp_path / "transform.py"
        transform_file.write_text(TRANSFORM_CODE)

        output_dir = tmp_path / "output"

        result = runner.invoke(
            typer_app,
            [
                "transform",
                str(transform_file),
                "-o",
                str(output_dir),
                str(data_dir / "entity_0.yaml"),
                str(data_dir / "entity_1.yaml"),
            ],
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        nodes_file = output_dir / "transform_nodes.tsv"
        assert nodes_file.exists()
        lines = nodes_file.read_text().strip().split("\n")
        # Header + 2 data rows
        assert len(lines) == 3

    def test_config_free_with_format_override(self, tmp_path):
        """Config-free mode with explicit format specification."""
        from typer.testing import CliRunner

        from koza.main import typer_app

        runner = CliRunner()

        # Create sample data files with non-standard extension
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "entity.dat").write_text("id: entity_1\nname: Entity 1\n")

        # Create a simple transform
        transform_file = tmp_path / "transform.py"
        transform_file.write_text(TRANSFORM_CODE)

        output_dir = tmp_path / "output"

        result = runner.invoke(
            typer_app,
            [
                "transform",
                str(transform_file),
                "--input-format",
                "yaml",
                "-o",
                str(output_dir),
                str(data_dir / "entity.dat"),
            ],
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        nodes_file = output_dir / "transform_nodes.tsv"
        assert nodes_file.exists()

    def test_config_free_csv_auto_delimiter(self, tmp_path):
        """Config-free mode auto-detects comma delimiter for .csv files."""
        from typer.testing import CliRunner

        from koza.main import typer_app

        runner = CliRunner()

        # Create sample CSV file with comma delimiter
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "data.csv").write_text("id,name\nentity_1,Entity 1\nentity_2,Entity 2\n")

        transform_file = tmp_path / "transform.py"
        transform_file.write_text(TRANSFORM_CODE)

        output_dir = tmp_path / "output"

        result = runner.invoke(
            typer_app,
            [
                "transform",
                str(transform_file),
                "-o",
                str(output_dir),
                str(data_dir / "data.csv"),
            ],
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        nodes_file = output_dir / "transform_nodes.tsv"
        assert nodes_file.exists()
        lines = nodes_file.read_text().strip().split("\n")
        # Header + 2 data rows
        assert len(lines) == 3

    def test_config_free_tsv_auto_delimiter(self, tmp_path):
        """Config-free mode auto-detects tab delimiter for .tsv files."""
        from typer.testing import CliRunner

        from koza.main import typer_app

        runner = CliRunner()

        # Create sample TSV file with tab delimiter
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "data.tsv").write_text("id\tname\nentity_1\tEntity 1\nentity_2\tEntity 2\n")

        transform_file = tmp_path / "transform.py"
        transform_file.write_text(TRANSFORM_CODE)

        output_dir = tmp_path / "output"

        result = runner.invoke(
            typer_app,
            [
                "transform",
                str(transform_file),
                "-o",
                str(output_dir),
                str(data_dir / "data.tsv"),
            ],
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        nodes_file = output_dir / "transform_nodes.tsv"
        assert nodes_file.exists()
        lines = nodes_file.read_text().strip().split("\n")
        # Header + 2 data rows
        assert len(lines) == 3

    def test_config_free_explicit_delimiter(self, tmp_path):
        """Config-free mode with explicit delimiter override."""
        from typer.testing import CliRunner

        from koza.main import typer_app

        runner = CliRunner()

        # Create sample file with pipe delimiter and non-standard extension
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "data.txt").write_text("id|name\nentity_1|Entity 1\n")

        transform_file = tmp_path / "transform.py"
        transform_file.write_text(TRANSFORM_CODE)

        output_dir = tmp_path / "output"

        result = runner.invoke(
            typer_app,
            [
                "transform",
                str(transform_file),
                "--input-format",
                "csv",
                "-d",
                "|",
                "-o",
                str(output_dir),
                str(data_dir / "data.txt"),
            ],
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        nodes_file = output_dir / "transform_nodes.tsv"
        assert nodes_file.exists()
        lines = nodes_file.read_text().strip().split("\n")
        # Header + 1 data row
        assert len(lines) == 2
