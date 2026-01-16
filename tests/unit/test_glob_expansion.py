"""Tests for glob pattern expansion in Source class."""

from pathlib import Path

import pytest

from koza.model.formats import InputFormat
from koza.model.reader import YAMLReaderConfig
from koza.model.source import Source


class TestExpandFilePatterns:
    """Test the _expand_file_patterns method in Source class."""

    def test_basic_glob_matches_files(self, tmp_path):
        """*.yaml matches all yaml files in directory."""
        # Create test files
        (tmp_path / "file1.yaml").write_text("name: test1")
        (tmp_path / "file2.yaml").write_text("name: test2")
        (tmp_path / "file3.yaml").write_text("name: test3")
        (tmp_path / "other.txt").write_text("not yaml")

        config = YAMLReaderConfig(files=["*.yaml"])
        source = Source(config, base_directory=tmp_path)

        expanded = source._expand_file_patterns(config.files)

        assert len(expanded) == 3
        assert all(p.suffix == ".yaml" for p in expanded)

    def test_subdirectory_glob(self, tmp_path):
        """subdir/*.yaml matches files in subdirectory."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file1.yaml").write_text("name: test1")
        (subdir / "file2.yaml").write_text("name: test2")
        (tmp_path / "root.yaml").write_text("name: root")

        config = YAMLReaderConfig(files=["subdir/*.yaml"])
        source = Source(config, base_directory=tmp_path)

        expanded = source._expand_file_patterns(config.files)

        assert len(expanded) == 2
        assert all("subdir" in str(p) for p in expanded)

    def test_recursive_glob(self, tmp_path):
        """**/*.yaml matches files at any depth."""
        # Create nested structure
        (tmp_path / "root.yaml").write_text("name: root")
        level1 = tmp_path / "level1"
        level1.mkdir()
        (level1 / "l1.yaml").write_text("name: l1")
        level2 = level1 / "level2"
        level2.mkdir()
        (level2 / "l2.yaml").write_text("name: l2")

        config = YAMLReaderConfig(files=["**/*.yaml"])
        source = Source(config, base_directory=tmp_path)

        expanded = source._expand_file_patterns(config.files)

        assert len(expanded) == 3

    def test_explicit_path_unchanged(self, tmp_path):
        """Paths without glob chars returned as-is."""
        (tmp_path / "explicit.yaml").write_text("name: explicit")

        config = YAMLReaderConfig(files=["explicit.yaml"])
        source = Source(config, base_directory=tmp_path)

        expanded = source._expand_file_patterns(config.files)

        assert len(expanded) == 1
        assert expanded[0] == tmp_path / "explicit.yaml"

    def test_relative_resolved_against_base_dir(self, tmp_path):
        """Relative patterns use base_directory."""
        (tmp_path / "test.yaml").write_text("name: test")

        config = YAMLReaderConfig(files=["test.yaml"])
        source = Source(config, base_directory=tmp_path)

        expanded = source._expand_file_patterns(config.files)

        assert len(expanded) == 1
        assert expanded[0].is_absolute()
        assert expanded[0].parent == tmp_path

    def test_absolute_path_unchanged(self, tmp_path):
        """Absolute patterns ignore base_directory."""
        test_file = tmp_path / "test.yaml"
        test_file.write_text("name: test")

        config = YAMLReaderConfig(files=[str(test_file)])
        # Use a different base directory
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        source = Source(config, base_directory=other_dir)

        expanded = source._expand_file_patterns(config.files)

        assert len(expanded) == 1
        assert expanded[0] == test_file

    def test_mixed_explicit_and_glob(self, tmp_path):
        """Can combine explicit paths with globs."""
        (tmp_path / "explicit.yaml").write_text("name: explicit")
        (tmp_path / "glob1.yaml").write_text("name: glob1")
        (tmp_path / "glob2.yaml").write_text("name: glob2")

        config = YAMLReaderConfig(files=["explicit.yaml", "glob*.yaml"])
        source = Source(config, base_directory=tmp_path)

        expanded = source._expand_file_patterns(config.files)

        # explicit.yaml + glob1.yaml + glob2.yaml
        assert len(expanded) == 3

    def test_no_matches_returns_literal(self, tmp_path):
        """Pattern with no matches treated as literal path."""
        config = YAMLReaderConfig(files=["nonexistent/*.yaml"])
        source = Source(config, base_directory=tmp_path)

        expanded = source._expand_file_patterns(config.files)

        # Should return the pattern as a literal path
        assert len(expanded) == 1
        assert "nonexistent" in str(expanded[0])

    def test_results_sorted(self, tmp_path):
        """Matched files returned in sorted order."""
        (tmp_path / "c.yaml").write_text("name: c")
        (tmp_path / "a.yaml").write_text("name: a")
        (tmp_path / "b.yaml").write_text("name: b")

        config = YAMLReaderConfig(files=["*.yaml"])
        source = Source(config, base_directory=tmp_path)

        expanded = source._expand_file_patterns(config.files)

        names = [p.name for p in expanded]
        assert names == ["a.yaml", "b.yaml", "c.yaml"]

    def test_character_class_glob(self, tmp_path):
        """[abc] patterns work correctly."""
        (tmp_path / "file_a.yaml").write_text("name: a")
        (tmp_path / "file_b.yaml").write_text("name: b")
        (tmp_path / "file_c.yaml").write_text("name: c")
        (tmp_path / "file_d.yaml").write_text("name: d")

        config = YAMLReaderConfig(files=["file_[abc].yaml"])
        source = Source(config, base_directory=tmp_path)

        expanded = source._expand_file_patterns(config.files)

        assert len(expanded) == 3
        names = [p.name for p in expanded]
        assert "file_d.yaml" not in names

    def test_question_mark_glob(self, tmp_path):
        """? wildcard matches single character."""
        (tmp_path / "file1.yaml").write_text("name: 1")
        (tmp_path / "file2.yaml").write_text("name: 2")
        (tmp_path / "file10.yaml").write_text("name: 10")

        config = YAMLReaderConfig(files=["file?.yaml"])
        source = Source(config, base_directory=tmp_path)

        expanded = source._expand_file_patterns(config.files)

        assert len(expanded) == 2
        names = [p.name for p in expanded]
        assert "file10.yaml" not in names
