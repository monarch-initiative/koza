"""Filtered rows are logged at DEBUG via deferred formatting.

The message must be DEBUG-level (so a normal run, whose sink defaults to INFO,
stays quiet) and only render the row when DEBUG is actually enabled.
"""

from pathlib import Path

from loguru import logger

from koza.model.reader import CSVReaderConfig
from koza.model.source import Source


def _filtered_source(tmp_path: Path) -> Source:
    """A 3-row TSV with a filter that keeps only `keep == yes` (drops row 2)."""
    data = tmp_path / "data.tsv"
    data.write_text("id\tkeep\n1\tyes\n2\tno\n3\tyes\n")
    config = CSVReaderConfig(
        files=[str(data)],
        delimiter="\t",
        # dict form, as loaded from a config YAML (ColumnFilter is a discriminated union)
        filters=[{"column": "keep", "inclusion": "include", "filter_code": "eq", "value": "yes"}],
    )
    return Source(config, base_directory=tmp_path)


def _capture(level: str, tmp_path: Path) -> list[str]:
    messages: list[str] = []
    sink_id = logger.add(messages.append, level=level, format="{message}")
    try:
        rows = list(_filtered_source(tmp_path))
    finally:
        logger.remove(sink_id)
    assert [r["id"] for r in rows] == ["1", "3"]  # filtering still works
    return messages


def test_filtered_row_logged_at_debug(tmp_path):
    captured = "".join(_capture("DEBUG", tmp_path))
    assert "Row filtered out" in captured
    assert "'keep': 'no'" in captured  # the dropped row is rendered when DEBUG is on


def test_filtered_row_silent_at_info(tmp_path):
    # The CLI sink defaults to INFO; the per-row debug line must not surface there.
    captured = "".join(_capture("INFO", tmp_path))
    assert "Row filtered out" not in captured
