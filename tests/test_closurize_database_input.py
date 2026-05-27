"""Tests for closurize's database-shape preconditions: errors when the
DuckDB doesn't exist, errors when required tables are missing."""

from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb
import pytest

from koza.graph_operations._closurize_engine import add_closure


def test_database_input_missing_tables():
    """If the DuckDB exists but lacks an `edges` table, closurize raises."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        incomplete_db_path = temp_path / "incomplete.duckdb"
        db = duckdb.connect(str(incomplete_db_path))
        db.sql("CREATE TABLE nodes (id VARCHAR, name VARCHAR)")
        db.close()

        closure_file = temp_path / "closure.tsv"
        closure_file.write_text("A\trdfs:subClassOf\tB")

        with pytest.raises(Exception):
            add_closure(
                database_path=str(incomplete_db_path),
                closure_file=str(closure_file),
            )


def test_missing_database_raises():
    """Closurize refuses to run when the database file doesn't exist."""
    with pytest.raises(ValueError, match="database_path does not exist"):
        add_closure(
            database_path="/nonexistent/path/to.duckdb",
            closure_file="closure.tsv",
        )
