"""Integration tests for glob pattern expansion in the transform pipeline."""

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


class TestGlobPipeline:
    """Test full pipeline with glob patterns."""

    def test_yaml_directory_ingest(self, tmp_path):
        """Full pipeline: directory of YAML files yields records from all files."""
        # Create sample YAML files
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        for i in range(3):
            (data_dir / f"entity_{i}.yaml").write_text(f"id: entity_{i}\nname: Entity {i}\n")

        # Create a simple transform
        transform_file = tmp_path / "transform.py"
        transform_file.write_text(TRANSFORM_CODE)

        config = KozaConfig(
            name="yaml-glob-test",
            reader=YAMLReaderConfig(files=["data/*.yaml"]),
            transform=TransformConfig(code="transform.py"),
            writer=WriterConfig(format=OutputFormat.tsv, node_properties=DEFAULT_NODE_PROPERTIES),
        )

        output_dir = str(tmp_path / "output")
        runner = KozaRunner.from_config(
            config, base_directory=tmp_path, output_dir=output_dir, row_limit=0, show_progress=False
        )
        runner.run()

        # Verify output has records from all 3 files
        nodes_file = Path(output_dir) / "yaml-glob-test_nodes.tsv"
        assert nodes_file.exists()
        lines = nodes_file.read_text().strip().split("\n")
        # Header + 3 data rows
        assert len(lines) == 4

    def test_json_directory_ingest(self, tmp_path):
        """Full pipeline: directory of JSON files yields records from all files."""
        # Create sample JSON files
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        for i in range(3):
            (data_dir / f"item_{i}.json").write_text(f'{{"id": "item_{i}", "name": "Item {i}"}}')

        # Create a simple transform
        transform_file = tmp_path / "transform.py"
        transform_file.write_text(TRANSFORM_CODE)

        config = KozaConfig(
            name="json-glob-test",
            reader=JSONReaderConfig(files=["data/*.json"]),
            transform=TransformConfig(code="transform.py"),
            writer=WriterConfig(format=OutputFormat.tsv, node_properties=DEFAULT_NODE_PROPERTIES),
        )

        output_dir = str(tmp_path / "output")
        runner = KozaRunner.from_config(
            config, base_directory=tmp_path, output_dir=output_dir, row_limit=0, show_progress=False
        )
        runner.run()

        # Verify output has records from all 3 files
        nodes_file = Path(output_dir) / "json-glob-test_nodes.tsv"
        assert nodes_file.exists()
        lines = nodes_file.read_text().strip().split("\n")
        # Header + 3 data rows
        assert len(lines) == 4

    def test_csv_partitioned_ingest(self, tmp_path):
        """Full pipeline: partitioned TSV files combined."""
        # Create sample TSV files
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        for i in range(2):
            (data_dir / f"2024-0{i+1}.tsv").write_text(f"id\tname\nrow_{i}_1\tName {i} 1\nrow_{i}_2\tName {i} 2\n")

        # Create a simple transform
        transform_file = tmp_path / "transform.py"
        transform_file.write_text(TRANSFORM_CODE)

        config = KozaConfig(
            name="csv-glob-test",
            reader=CSVReaderConfig(files=["data/2024-*.tsv"], delimiter="\t"),
            transform=TransformConfig(code="transform.py"),
            writer=WriterConfig(format=OutputFormat.tsv, node_properties=DEFAULT_NODE_PROPERTIES),
        )

        output_dir = str(tmp_path / "output")
        runner = KozaRunner.from_config(
            config, base_directory=tmp_path, output_dir=output_dir, row_limit=0, show_progress=False
        )
        runner.run()

        # Verify output has records from both files (2 rows each)
        nodes_file = Path(output_dir) / "csv-glob-test_nodes.tsv"
        assert nodes_file.exists()
        lines = nodes_file.read_text().strip().split("\n")
        # Header + 4 data rows (2 per file)
        assert len(lines) == 5

    def test_recursive_glob_pattern(self, tmp_path):
        """Full pipeline: recursive glob pattern works."""
        # Create nested directory structure
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "root.yaml").write_text("id: root\nname: Root\n")

        sub1 = data_dir / "sub1"
        sub1.mkdir()
        (sub1 / "nested1.yaml").write_text("id: nested1\nname: Nested 1\n")

        sub2 = sub1 / "sub2"
        sub2.mkdir()
        (sub2 / "deep.yaml").write_text("id: deep\nname: Deep\n")

        # Create a simple transform
        transform_file = tmp_path / "transform.py"
        transform_file.write_text(TRANSFORM_CODE)

        config = KozaConfig(
            name="recursive-glob-test",
            reader=YAMLReaderConfig(files=["data/**/*.yaml"]),
            transform=TransformConfig(code="transform.py"),
            writer=WriterConfig(format=OutputFormat.tsv, node_properties=DEFAULT_NODE_PROPERTIES),
        )

        output_dir = str(tmp_path / "output")
        runner = KozaRunner.from_config(
            config, base_directory=tmp_path, output_dir=output_dir, row_limit=0, show_progress=False
        )
        runner.run()

        # Verify output has records from all 3 files at different depths
        nodes_file = Path(output_dir) / "recursive-glob-test_nodes.tsv"
        assert nodes_file.exists()
        lines = nodes_file.read_text().strip().split("\n")
        # Header + 3 data rows
        assert len(lines) == 4

    def test_mixed_explicit_and_glob_patterns(self, tmp_path):
        """Full pipeline: mix of explicit paths and glob patterns."""
        # Create files
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "explicit.yaml").write_text("id: explicit\nname: Explicit\n")
        (data_dir / "glob1.yaml").write_text("id: glob1\nname: Glob 1\n")
        (data_dir / "glob2.yaml").write_text("id: glob2\nname: Glob 2\n")
        (data_dir / "other.txt").write_text("not yaml")

        # Create a simple transform
        transform_file = tmp_path / "transform.py"
        transform_file.write_text(TRANSFORM_CODE)

        config = KozaConfig(
            name="mixed-glob-test",
            reader=YAMLReaderConfig(files=["data/explicit.yaml", "data/glob*.yaml"]),
            transform=TransformConfig(code="transform.py"),
            writer=WriterConfig(format=OutputFormat.tsv, node_properties=DEFAULT_NODE_PROPERTIES),
        )

        output_dir = str(tmp_path / "output")
        runner = KozaRunner.from_config(
            config, base_directory=tmp_path, output_dir=output_dir, row_limit=0, show_progress=False
        )
        runner.run()

        # Verify output has records from explicit + 2 glob matches
        nodes_file = Path(output_dir) / "mixed-glob-test_nodes.tsv"
        assert nodes_file.exists()
        lines = nodes_file.read_text().strip().split("\n")
        # Header + 3 data rows
        assert len(lines) == 4


class TestConfigFreeTransform:
    """Test config-free transform mode via CLI."""

    def test_config_free_yaml_pipeline(self, tmp_path):
        """Config-free mode processes YAML directory."""
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
                "-i",
                str(data_dir / "*.yaml"),
                "-o",
                str(output_dir),
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
                "-i",
                str(data_dir / "entity.dat"),
                "--input-format",
                "yaml",
                "-o",
                str(output_dir),
            ],
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        nodes_file = output_dir / "transform_nodes.tsv"
        assert nodes_file.exists()
