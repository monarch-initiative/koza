import tempfile
from pathlib import Path

from typer.testing import CliRunner

from koza.main import typer_app

runner = CliRunner()


def test_cli():
    config_file = (Path(__file__).parent / "../../examples/string/protein-links-detailed.yaml").resolve()
    test_output_dir = (Path(__file__).parent / "../output").resolve()

    with tempfile.TemporaryDirectory(dir=test_output_dir) as output_dir:
        result = runner.invoke(
            typer_app,
            [
                "transform",
                str(config_file),
                "--output-dir",
                output_dir,
            ],
        )

        nodes_output = Path(output_dir) / "protein-links-detailed_nodes.tsv"
        edges_output = Path(output_dir) / "protein-links-detailed_edges.tsv"

        assert nodes_output.exists()
        assert edges_output.exists()

        assert result.exit_code == 0
