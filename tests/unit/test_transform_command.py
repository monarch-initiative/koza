"""Tests for transform command helper functions and CLI."""

from pathlib import Path

import pytest

from koza.main import _expand_cli_file_patterns, _infer_input_format
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


class TestExpandCliFilePatterns:
    """Test the _expand_cli_file_patterns function."""

    def test_expands_glob_pattern(self, tmp_path):
        """Glob patterns are expanded."""
        (tmp_path / "file1.yaml").write_text("test")
        (tmp_path / "file2.yaml").write_text("test")

        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            expanded = _expand_cli_file_patterns(["*.yaml"])
            assert len(expanded) == 2
        finally:
            os.chdir(old_cwd)

    def test_literal_path_unchanged(self, tmp_path):
        """Paths without glob chars returned as-is."""
        expanded = _expand_cli_file_patterns(["explicit.yaml"])
        assert expanded == ["explicit.yaml"]

    def test_no_matches_returns_literal(self, tmp_path):
        """Pattern with no matches treated as literal path."""
        expanded = _expand_cli_file_patterns(["nonexistent/*.yaml"])
        assert expanded == ["nonexistent/*.yaml"]

    def test_results_sorted(self, tmp_path):
        """Matched files returned in sorted order."""
        (tmp_path / "c.yaml").write_text("test")
        (tmp_path / "a.yaml").write_text("test")
        (tmp_path / "b.yaml").write_text("test")

        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            expanded = _expand_cli_file_patterns(["*.yaml"])
            assert expanded == ["a.yaml", "b.yaml", "c.yaml"]
        finally:
            os.chdir(old_cwd)

    def test_recursive_glob(self, tmp_path):
        """**/*.yaml matches files at any depth."""
        (tmp_path / "root.yaml").write_text("test")
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "nested.yaml").write_text("test")

        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            expanded = _expand_cli_file_patterns(["**/*.yaml"])
            assert len(expanded) == 2
        finally:
            os.chdir(old_cwd)


class TestTransformCommand:
    """Test transform command behavior via CLI runner."""

    def test_py_extension_requires_input_flag(self, tmp_path):
        """.py file without -i raises BadParameter."""
        from typer.testing import CliRunner

        from koza.main import typer_app

        runner = CliRunner()
        transform_file = tmp_path / "transform.py"
        transform_file.write_text("# empty transform")

        result = runner.invoke(typer_app, ["transform", str(transform_file)])

        assert result.exit_code != 0
        assert "--input-file/-i required" in result.output or "required" in result.output.lower()

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

        # Should fail because config is invalid, but not with "requires -i"
        assert "--input-file/-i required" not in result.output
