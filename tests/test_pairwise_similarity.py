"""Tests for the pairwise-similarity operation: all-by-all term similarity
(Jaccard, Resnik, Phenodigm) between two term sets over a closurized graph,
semsimian's `all_by_all_pairwise_similarity`, computed in DuckDB.

Hand-checkable fixture (reflexive rdfs:subClassOf closure):

    ROOT
     ├── A ── A1, A2      (A1, A2 under A)
     └── B ── B1          (B1 under B)
    XROOT ── X1 ── X2     (other prefix; X2 also under A)

Term sets: subjects = HP-prefixed descendants of A (A, A1, A2),
objects = descendants of ROOT with prefix HP or X.
"""

from __future__ import annotations

import math

import duckdb
import pytest

from koza.graph_operations import compute_pairwise_similarity
from koza.graph_operations.utils import GraphDatabase
from koza.model.graph_operations import PairwiseSimilarityConfig

ANCESTORS = {  # term -> reflexive ancestors
    "HP:ROOT": {"HP:ROOT"},
    "HP:A": {"HP:A", "HP:ROOT"},
    "HP:A1": {"HP:A1", "HP:A", "HP:ROOT"},
    "HP:A2": {"HP:A2", "HP:A", "HP:ROOT"},
    "HP:B": {"HP:B", "HP:ROOT"},
    "HP:B1": {"HP:B1", "HP:B", "HP:ROOT"},
    "X:ROOT": {"X:ROOT"},
    "X:1": {"X:1", "X:ROOT", "HP:ROOT"},
    "X:2": {"X:2", "X:1", "X:ROOT", "HP:A", "HP:ROOT"},
}
# IC; HP:A1 and HP:A2 tie, X:1 deliberately absent (ancestors without IC are ignored)
IC = {"HP:ROOT": 0.0, "HP:A": 2.0, "HP:A1": 4.0, "HP:A2": 4.0, "HP:B": 1.0, "HP:B1": 3.0,
      "X:ROOT": 0.0, "X:2": 5.0}
LABELS = {"HP:A": "a", "HP:A1": "a one", "HP:A2": "a two", "HP:B": "b", "HP:B1": "b one", "X:2": "x two"}


@pytest.fixture
def kg(tmp_path):
    db_path = tmp_path / "kg.duckdb"
    with GraphDatabase(db_path) as db:
        c = db.conn
        c.execute("CREATE TABLE closure (subject_id VARCHAR, predicate_id VARCHAR, object_id VARCHAR)")
        for t, ancs in ANCESTORS.items():
            for a in ancs:
                c.execute("INSERT INTO closure VALUES (?, 'rdfs:subClassOf', ?)", [t, a])
        c.execute("INSERT INTO closure VALUES ('HP:A1', 'BFO:0000050', 'HP:B')")  # must be ignored
        c.execute("CREATE TABLE information_content_x (term VARCHAR, ic DOUBLE)")
        c.executemany("INSERT INTO information_content_x VALUES (?, ?)", list(IC.items()))
        c.execute("CREATE TABLE nodes (id VARCHAR, name VARCHAR)")
        c.executemany("INSERT INTO nodes VALUES (?, ?)", list(LABELS.items()))
    return db_path


def expected(subjects, objects, threshold):
    rows = {}
    for s in subjects:
        for o in objects:
            common = ANCESTORS[s] & ANCESTORS[o]
            scored = [(IC[a], a) for a in common if a in IC]
            if not scored:
                continue
            resnik = max(ic for ic, _ in scored)
            if not resnik > threshold:
                continue
            mica = min(a for ic, a in scored if ic == resnik)
            jac = len(common) / len(ANCESTORS[s] | ANCESTORS[o])
            rows[(s, o)] = (mica, resnik, jac, math.sqrt(resnik * jac))
    return rows


def _config(db_path, out, **kw):
    base = dict(
        database_path=db_path, output_path=out, ic_table="information_content_x",
        subject_root="HP:A", subject_prefixes=["HP"],
        object_root="HP:ROOT", object_prefixes=["HP", "X"],
        min_ancestor_information_content=1.5, batch_size=2, quiet=True,
    )
    base.update(kw)
    return PairwiseSimilarityConfig(**base)


def _read(out):
    return duckdb.connect().execute(
        f"SELECT * FROM '{out}' ORDER BY subject_id, object_id").fetchdf()


@pytest.mark.parametrize("suffix", ["tsv", "parquet"])
def test_matches_hand_computed(kg, tmp_path, suffix):
    out = tmp_path / f"pairs.{suffix}"
    result = compute_pairwise_similarity(_config(kg, out))
    assert result.success
    subjects = ["HP:A", "HP:A1", "HP:A2"]
    objects = ["HP:A", "HP:A1", "HP:A2", "HP:B", "HP:B1", "HP:ROOT", "X:1", "X:2"]
    assert result.subject_count == 3 and result.object_count == len(objects)
    exp = expected(subjects, objects, 1.5)
    df = _read(out)
    got = {(r.subject_id, r.object_id): (r.ancestor_id, r.ancestor_information_content,
                                          r.jaccard_similarity, r.phenodigm_score) for r in df.itertuples()}
    assert got.keys() == exp.keys()
    for k, (mica, res, jac, ph) in exp.items():
        g = got[k]
        assert g[0] == mica, k
        assert g[1:] == pytest.approx((res, jac, ph)), k
    assert result.row_count == len(exp)


def test_strict_threshold_and_tie_break(kg, tmp_path):
    out = tmp_path / "pairs.tsv"
    compute_pairwise_similarity(_config(kg, out, min_ancestor_information_content=2.0))
    df = _read(out)
    pairs = set(zip(df.subject_id, df.object_id))
    # (HP:A, HP:A) shares HP:A with IC exactly 2.0 -> excluded by the strict ">" cutoff
    assert ("HP:A", "HP:A") not in pairs
    # (HP:A1, HP:A1): max IC 4.0 from HP:A1 itself
    row = df[(df.subject_id == "HP:A1") & (df.object_id == "HP:A1")].iloc[0]
    assert row.ancestor_id == "HP:A1"


def test_labels_and_columns(kg, tmp_path):
    out = tmp_path / "pairs.tsv"
    compute_pairwise_similarity(_config(kg, out))
    df = _read(out)
    assert list(df.columns) == [
        "subject_id", "subject_label", "object_id", "object_label", "ancestor_id", "ancestor_label",
        "ancestor_information_content", "jaccard_similarity", "phenodigm_score",
    ]
    r = df[(df.subject_id == "HP:A1") & (df.object_id == "X:2")].iloc[0]
    assert (r.subject_label, r.object_label, r.ancestor_label) == ("a one", "x two", "a")


def test_ancestors_without_ic_are_ignored(kg, tmp_path):
    out = tmp_path / "pairs.tsv"
    compute_pairwise_similarity(_config(kg, out, min_ancestor_information_content=-1.0))
    df = _read(out)
    # (HP:A, X:1) share only HP:ROOT (IC 0.0): kept at threshold -1, Resnik 0
    r = df[(df.subject_id == "HP:A") & (df.object_id == "X:1")].iloc[0]
    assert r.ancestor_id == "HP:ROOT" and r.ancestor_information_content == 0.0


def test_does_not_modify_database(kg, tmp_path):
    with GraphDatabase(kg) as db:
        before = sorted(r[0] for r in db.conn.execute("SHOW TABLES").fetchall())
    compute_pairwise_similarity(_config(kg, tmp_path / "pairs.tsv"))
    with GraphDatabase(kg) as db:
        after = sorted(r[0] for r in db.conn.execute("SHOW TABLES").fetchall())
    assert before == after
    assert not list(tmp_path.glob("*.work.duckdb*"))  # scratch database cleaned up


def test_missing_ic_table_fails(kg, tmp_path):
    with pytest.raises(Exception, match="no_such_ic"):
        compute_pairwise_similarity(_config(kg, tmp_path / "p.tsv", ic_table="no_such_ic"))


ALL_SUBJECTS = ["HP:A", "HP:A1", "HP:A2"]
ALL_OBJECTS = ["HP:A", "HP:A1", "HP:A2", "HP:B", "HP:B1", "HP:ROOT", "X:1", "X:2"]


def _assert_matches_expected(out, threshold=1.5):
    exp = expected(ALL_SUBJECTS, ALL_OBJECTS, threshold)
    df = _read(out)
    got = {(r.subject_id, r.object_id): (r.ancestor_id, r.ancestor_information_content,
                                          r.jaccard_similarity, r.phenodigm_score) for r in df.itertuples()}
    assert got.keys() == exp.keys()
    for k, (mica, res, jac, ph) in exp.items():
        assert got[k][0] == mica, k
        assert got[k][1:] == pytest.approx((res, jac, ph)), k
    return df


def test_closure_without_self_rows(kg, tmp_path):
    """anc(t) is reflexive whether or not the closure carries (t, t) rows."""
    with GraphDatabase(kg) as db:
        db.conn.execute("DELETE FROM closure WHERE subject_id = object_id AND subject_id NOT IN ('HP:A', 'HP:ROOT')")
    out = tmp_path / "pairs.tsv"
    compute_pairwise_similarity(_config(kg, out))
    df = _assert_matches_expected(out)
    # sibling leaves must not look identical
    r = df[(df.subject_id == "HP:A1") & (df.object_id == "HP:A2")].iloc[0]
    assert r.jaccard_similarity == pytest.approx(2 / 4) and r.ancestor_id == "HP:A"


def test_duplicate_ic_rows_do_not_inflate_jaccard(kg, tmp_path):
    with GraphDatabase(kg) as db:
        db.conn.executemany("INSERT INTO information_content_x VALUES (?, ?)", list(IC.items()))
    out = tmp_path / "pairs.tsv"
    compute_pairwise_similarity(_config(kg, out))
    df = _assert_matches_expected(out)
    assert (df.jaccard_similarity <= 1.0).all()


def test_duplicate_node_rows_do_not_multiply_output(kg, tmp_path):
    with GraphDatabase(kg) as db:
        db.conn.executemany("INSERT INTO nodes VALUES (?, ?)", list(LABELS.items()))
    out = tmp_path / "pairs.tsv"
    result = compute_pairwise_similarity(_config(kg, out))
    _assert_matches_expected(out)
    assert len(_read(out)) == result.row_count


def test_output_is_sorted(kg, tmp_path):
    out = tmp_path / "pairs.tsv"
    compute_pairwise_similarity(_config(kg, out, batch_size=1))
    df = duckdb.connect().execute(f"SELECT subject_id, object_id FROM '{out}'").fetchdf()
    keys = list(zip(df.subject_id, df.object_id, strict=True))
    assert keys == sorted(keys)
