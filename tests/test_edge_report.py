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


@pytest.fixture
def kg_translator(tmp_path):
    """A translator-style graph: knowledge source lives inside a nested
    `sources: [{resource_id, resource_role}]` struct array (no flat column), plus
    a `publications` list and a numeric `has_confidence_score`."""
    db = tmp_path / "kg.duckdb"
    conn = duckdb.connect(str(db))
    conn.execute(
        """
        CREATE TABLE nodes AS
        SELECT 'GENE:' || i AS id, 'biolink:Gene' AS category FROM range(3) t(i)
        UNION ALL SELECT 'MONDO:' || i, 'biolink:Disease' FROM range(3) t(i);

        CREATE TABLE edges AS
        SELECT
            'GENE:' || (i % 3)::VARCHAR AS subject,
            'biolink:causes'           AS predicate,
            'MONDO:' || (i % 3)::VARCHAR AS object,
            [{'resource_id': ['infores:ctd','infores:signor'][(i % 2) + 1],
              'resource_role': 'primary_knowledge_source'}] AS sources,
            -- 0, 1, or 2 publications depending on the row
            ['PMID:1','PMID:2'][1:(i % 3)]  AS publications,
            (i % 5)::DOUBLE                 AS has_confidence_score
        FROM range(15) t(i);
        """
    )
    conn.close()
    return db


def test_source_role_derived_from_sources_struct_array(kg_translator, tmp_path):
    """primary_knowledge_source is pulled out of the nested sources[] and reported
    as the distinct set of resource_ids for that role."""
    out = tmp_path / "summary.parquet"
    generate_edge_report(
        EdgeReportConfig(
            database_path=kg_translator,
            output_file=out,
            output_format="parquet",
            categorical_columns=["subject_category", "predicate", "object_category"],
            set_columns=["primary_knowledge_source"],
            quiet=True,
        )
    )
    df = _read(out)
    assert sorted(df["primary_knowledge_source"].iloc[0]) == ["infores:ctd", "infores:signor"]


def test_percentile_columns_for_list_and_numeric(kg_translator, tmp_path):
    """List slots summarize element count (missing → 0); numeric slots the value."""
    out = tmp_path / "summary.parquet"
    generate_edge_report(
        EdgeReportConfig(
            database_path=kg_translator,
            output_file=out,
            output_format="parquet",
            categorical_columns=["subject_category", "predicate", "object_category"],
            percentile_columns=["publications", "has_confidence_score"],
            quiet=True,
        )
    )
    df = _read(out)
    row = df.iloc[0]
    # publications per edge cycle 0,1,2 → mean 1.0, min 0, max 2
    assert row["publications_avg"] == pytest.approx(1.0, abs=0.01)
    q = list(row["publications_quantiles"])
    assert q[0] == 0 and q[-1] == 2
    # has_confidence_score cycles 0..4 → min 0, max 4
    cq = list(row["has_confidence_score_quantiles"])
    assert cq[0] == pytest.approx(0.0) and cq[-1] == pytest.approx(4.0)


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


def _capture_logs(level="DEBUG"):
    """Capture loguru records (koza logs via loguru, not stdlib logging)."""
    from loguru import logger

    records: list[tuple[str, str]] = []
    sink_id = logger.add(lambda m: records.append((m.record["level"].name, m.record["message"])), level=level)
    return records, sink_id


def test_absent_default_column_is_debug_not_warning(kg, tmp_path):
    """A default group column the graph lacks (provided_by here) is expected —
    debug, not a warning that reads like an error."""
    from loguru import logger

    records, sink_id = _capture_logs()
    try:
        generate_edge_report(
            EdgeReportConfig(  # no categorical_columns override -> uses defaults incl. provided_by
                database_path=kg, output_file=tmp_path / "r.parquet",
                output_format="parquet", quiet=True,
            )
        )
    finally:
        logger.remove(sink_id)
    assert not any(lvl == "WARNING" and "provided_by" in msg for lvl, msg in records)
    assert any(lvl == "DEBUG" and "provided_by" in msg for lvl, msg in records)


def test_absent_explicit_column_warns(kg, tmp_path):
    """A column the user explicitly asked for is still a warning when missing."""
    from loguru import logger

    records, sink_id = _capture_logs()
    try:
        generate_edge_report(
            EdgeReportConfig(
                database_path=kg, output_file=tmp_path / "r.parquet", output_format="parquet",
                categorical_columns=["subject_category", "predicate", "does_not_exist"],
                quiet=True,
            )
        )
    finally:
        logger.remove(sink_id)
    assert any(lvl == "WARNING" and "does_not_exist" in msg for lvl, msg in records)
