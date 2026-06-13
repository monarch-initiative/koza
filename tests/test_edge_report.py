"""Tests for the tabular edge report, including the kgxval-style SPQO summary.

The default report is a plain cross-tab (GROUP BY ALL + count). When `set_columns`
are given it switches to the "edge type shape" summary: one row per group, each set
column reported as the distinct set of values that group spans, plus an optional
`proportion` column.
"""

from __future__ import annotations

import duckdb
import pytest

from koza.graph_operations.report import generate_edge_report
from koza.model.graph_operations import EdgeReportConfig


@pytest.fixture
def kg(tmp_path):
    """A small graph with multiple knowledge_level / agent_type / source values per
    (subject_category, predicate, object_category) group, a list-typed source slot
    (aggregator_knowledge_source), and nodes WITHOUT an in_taxon slot (the denorm
    view must still build)."""
    db = tmp_path / "kg.duckdb"
    conn = duckdb.connect(str(db))
    conn.execute(
        """
        CREATE TABLE nodes AS
        SELECT 'GENE:' || i::VARCHAR AS id, 'biolink:Gene' AS category, 'g' || i AS name
        FROM range(4) t(i)
        UNION ALL
        SELECT 'MONDO:' || i::VARCHAR, 'biolink:Disease', 'd' || i
        FROM range(4) t(i);

        CREATE TABLE edges AS
        SELECT
            'e' || i::VARCHAR                                       AS id,
            'GENE:' || (i % 4)::VARCHAR                             AS subject,
            'MONDO:' || (i % 4)::VARCHAR                            AS object,
            'biolink:causes'                                       AS predicate,
            -- two distinct knowledge_level / agent_type values across the group
            ['knowledge_assertion','prediction'][(i % 2) + 1]       AS knowledge_level,
            ['manual_agent','automated_agent'][(i % 2) + 1]         AS agent_type,
            'infores:ctd'                                          AS primary_knowledge_source,
            -- list-typed: two aggregators per edge, varying across rows
            ['infores:a', ['infores:b','infores:c'][(i % 2) + 1]]   AS aggregator_knowledge_source
        FROM range(10) t(i);
        """
    )
    conn.close()
    return db


def _read(path, fmt="parquet"):
    return duckdb.sql(f"SELECT * FROM '{path}'").df()


def test_default_report_is_plain_crosstab(kg, tmp_path):
    """No set_columns → unchanged GROUP BY ALL behavior: count, no proportion/sets."""
    out = tmp_path / "report.parquet"
    generate_edge_report(
        EdgeReportConfig(
            database_path=kg,
            output_file=out,
            output_format="parquet",
            categorical_columns=["subject_category", "predicate", "object_category"],
            quiet=True,
        )
    )
    df = _read(out)
    assert set(df.columns) == {"subject_category", "predicate", "object_category", "count"}
    # all 10 edges collapse into the single Gene-causes-Disease group
    assert len(df) == 1
    assert int(df["count"].iloc[0]) == 10


def test_spqo_summary_aggregates_set_columns(kg, tmp_path):
    """set_columns are pulled out of the GROUP BY and reported as distinct sets."""
    out = tmp_path / "summary.parquet"
    generate_edge_report(
        EdgeReportConfig(
            database_path=kg,
            output_file=out,
            output_format="parquet",
            categorical_columns=["subject_category", "predicate", "object_category"],
            set_columns=["knowledge_level", "agent_type", "primary_knowledge_source"],
            include_proportion=True,
            quiet=True,
        )
    )
    df = _read(out)
    assert len(df) == 1
    row = df.iloc[0]
    assert int(row["count"]) == 10
    assert row["proportion"] == pytest.approx(1.0)
    assert sorted(row["knowledge_level"]) == ["knowledge_assertion", "prediction"]
    assert sorted(row["agent_type"]) == ["automated_agent", "manual_agent"]
    assert sorted(row["primary_knowledge_source"]) == ["infores:ctd"]
    # set columns must NOT appear as group dimensions
    assert "knowledge_level" not in {"subject_category", "predicate", "object_category"}


def test_list_typed_set_column_is_flattened(kg, tmp_path):
    """A VARCHAR[] set column yields the distinct set of *elements*, not lists."""
    out = tmp_path / "summary.parquet"
    generate_edge_report(
        EdgeReportConfig(
            database_path=kg,
            output_file=out,
            output_format="parquet",
            categorical_columns=["subject_category", "predicate", "object_category"],
            set_columns=["aggregator_knowledge_source"],
            quiet=True,
        )
    )
    df = _read(out)
    assert sorted(df["aggregator_knowledge_source"].iloc[0]) == [
        "infores:a",
        "infores:b",
        "infores:c",
    ]


def test_proportion_sums_to_one_across_groups(kg, tmp_path):
    """With a real split (group by knowledge_level), proportions sum to 1."""
    out = tmp_path / "summary.parquet"
    generate_edge_report(
        EdgeReportConfig(
            database_path=kg,
            output_file=out,
            output_format="parquet",
            categorical_columns=["predicate", "knowledge_level"],
            set_columns=["agent_type"],
            include_proportion=True,
            quiet=True,
        )
    )
    df = _read(out)
    assert len(df) == 2  # one row per knowledge_level
    assert df["proportion"].sum() == pytest.approx(1.0)
    assert int(df["count"].sum()) == 10


def test_missing_set_column_is_skipped_not_fatal(kg, tmp_path):
    """A set column absent from the graph is warned and dropped, not an error."""
    out = tmp_path / "summary.parquet"
    generate_edge_report(
        EdgeReportConfig(
            database_path=kg,
            output_file=out,
            output_format="parquet",
            categorical_columns=["subject_category", "predicate", "object_category"],
            set_columns=["knowledge_level", "does_not_exist"],
            quiet=True,
        )
    )
    df = _read(out)
    assert "knowledge_level" in df.columns
    assert "does_not_exist" not in df.columns
