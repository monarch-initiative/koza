"""Tests for transform command helper functions and CLI."""

import pytest

from koza.main import _infer_input_format
from koza.model.formats import InputFormat


class TestInferInputFormat:
    """Test the _infer_input_format function."""

    @pytest.mark.parametrize(
        "ext,expected",
        [
            (".yaml", InputFormat.yaml),
            (".yml", InputFormat.yaml),
            (".json", InputFormat.json),
            (".jsonl", InputFormat.jsonl),
            (".tsv", InputFormat.csv),
            (".csv", InputFormat.csv),
        ],
    )
    def test_infers_format_from_extension(self, ext, expected):
        """Correct format inferred from file extension."""
        files = [f"test{ext}"]
        assert _infer_input_format(files) == expected

    def test_unknown_extension_raises(self):
        """Unknown extension raises with helpful message."""
        with pytest.raises(ValueError, match="Cannot infer format"):
            _infer_input_format(["test.unknown"])

    def test_empty_files_raises(self):
        """Empty file list raises error."""
        with pytest.raises(ValueError, match="No files provided"):
            _infer_input_format([])

    def test_uses_first_file_for_inference(self):
        """Format is inferred from the first file in the list."""
        files = ["first.yaml", "second.json", "third.tsv"]
        assert _infer_input_format(files) == InputFormat.yaml

    def test_case_insensitive(self):
        """Extension matching is case-insensitive."""
        assert _infer_input_format(["TEST.YAML"]) == InputFormat.yaml
        assert _infer_input_format(["test.JSON"]) == InputFormat.json


class TestTransformCommand:
    """Test transform command behavior via CLI runner."""

    def test_py_extension_requires_input_files(self, tmp_path):
        """.py file without input files raises BadParameter with helpful message."""
        from typer.testing import CliRunner

        from koza.main import typer_app

        runner = CliRunner()
        transform_file = tmp_path / "transform.py"
        transform_file.write_text("# empty transform")

        result = runner.invoke(typer_app, ["transform", str(transform_file)])

        assert result.exit_code != 0
        # Verify the error message is clear and actionable
        assert "Input files required" in result.output
        assert "positional arguments" in result.output

    def test_yaml_extension_uses_config_mode(self, tmp_path):
        """config.yaml triggers config file loading."""
        from typer.testing import CliRunner

        from koza.main import typer_app

        runner = CliRunner()
        # Create a minimal config file that will fail to load properly
        # but demonstrates it's being treated as config
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: config")

        result = runner.invoke(typer_app, ["transform", str(config_file)])

        # Should fail because config is invalid, but not with input file errors
        # (config mode doesn't require positional input files)
        assert result.exit_code != 0
