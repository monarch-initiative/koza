"""Pairwise-similarity operation: all-by-all term similarity between two term
sets over a closurized graph database, computed in DuckDB.

Equivalent to semsimian's `all_by_all_pairwise_similarity` (what
`runoak similarity` runs): for subject s and object o, with anc(t) the reflexive
closure ancestors of t,

    jaccard_similarity            = |anc(s) & anc(o)| / |anc(s) | anc(o)|
    ancestor_information_content  = max IC over shared ancestors in `ic_table` (Resnik)
    ancestor_id                   = that ancestor; ties -> smallest id
    phenodigm_score               = sqrt(Resnik * Jaccard)

keeping pairs with Resnik strictly above `min_ancestor_information_content`.
Ancestors with no IC row are ignored for Resnik, as semsimian does with a custom
IC map. Rows and scores match semsimian exactly; only `ancestor_id` can differ
where several shared ancestors tie for the maximum IC (semsimian picks one
arbitrarily).

The graph database is attached read-only; subject terms are processed in
batches (`batch_size`) so the shared-ancestor join stays bounded, with
intermediates in a scratch DuckDB file beside the output.
"""

from __future__ import annotations

import time
from pathlib import Path

import duckdb
from loguru import logger

from koza.model.graph_operations import (
    OperationSummary,
    PairwiseSimilarityConfig,
    PairwiseSimilarityResult,
)

from .utils import curie_prefix_filter, print_operation_summary, sql_string_list


def _copy_options(output_path: Path) -> str:
    name = output_path.name
    if name.endswith(".parquet"):
        return "(FORMAT parquet)"
    if name.endswith(".tsv.gz"):
        return "(FORMAT csv, HEADER true, DELIMITER '\t', COMPRESSION gzip)"
    return "(FORMAT csv, HEADER true, DELIMITER '\t')"


def compute_pairwise_similarity(config: PairwiseSimilarityConfig) -> PairwiseSimilarityResult:
    """Write the all-by-all similarity table for `config` to `config.output_path`."""
    start_time = time.time()
    out = config.output_path
    work_db = out.with_name(out.name + ".work.duckdb")
    for f in (work_db, Path(str(work_db) + ".wal")):
        f.unlink(missing_ok=True)
    preds = sql_string_list(config.closure_predicates)
    cs, cp, co = config.closure_subject_column, config.closure_predicate_column, config.closure_object_column

    def term_set(root: str, prefixes: list[str] | None) -> str:
        return (f"SELECT DISTINCT {cs} AS t FROM kg.{config.closure_table} "
                f"WHERE {cp} IN ({preds}) AND {co} = {sql_string_list([root])}"
                f"{curie_prefix_filter(cs, prefixes)}")

    try:
        con = duckdb.connect(str(work_db))
        try:
            if config.memory_limit:
                con.execute(f"SET memory_limit = '{config.memory_limit}'")
            if config.threads:
                con.execute(f"SET threads = {int(config.threads)}")
            con.execute("SET preserve_insertion_order = false")
            con.execute(f"ATTACH {sql_string_list([str(config.database_path)])} AS kg (READ_ONLY)")

            con.execute(f"""CREATE TABLE s_terms AS
                SELECT t, ((row_number() OVER (ORDER BY t)) - 1) // {int(config.batch_size)} AS batch
                FROM ({term_set(config.subject_root, config.subject_prefixes)})""")
            con.execute(f"CREATE TABLE o_terms AS {term_set(config.object_root, config.object_prefixes)}")
            subject_count = con.execute("SELECT count(*) FROM s_terms").fetchone()[0]
            object_count = con.execute("SELECT count(*) FROM o_terms").fetchone()[0]
            logger.info(f"pairwise-similarity: {subject_count:,} subjects x {object_count:,} objects, "
                        f"ic_table={config.ic_table}, min_ancestor_ic>{config.min_ancestor_information_content}")

            # closure restricted to the compared terms; DISTINCT collapses multi-predicate duplicates
            con.execute(f"""CREATE TABLE clo AS
                SELECT DISTINCT c.{cs} AS t, c.{co} AS a FROM kg.{config.closure_table} c
                WHERE c.{cp} IN ({preds})
                  AND c.{cs} IN (SELECT t FROM s_terms UNION SELECT t FROM o_terms)""")
            con.execute("CREATE TABLE sz AS SELECT t, count(*) AS sz FROM clo GROUP BY t")
            con.execute("CREATE TABLE o_clo AS SELECT c.t, c.a FROM clo c JOIN o_terms o ON o.t = c.t")
            con.execute(f"CREATE TABLE ic AS SELECT term, ic FROM kg.{config.ic_table}")

            con.execute("""CREATE TABLE result (subject_id VARCHAR, object_id VARCHAR, ancestor_id VARCHAR,
                ancestor_information_content DOUBLE, jaccard_similarity DOUBLE, phenodigm_score DOUBLE)""")
            n_batches = con.execute("SELECT coalesce(max(batch) + 1, 0) FROM s_terms").fetchone()[0]
            for b in range(n_batches):
                con.execute("""
                    INSERT INTO result
                    WITH common AS (
                        SELECT sc.t AS s, oc.t AS o, sc.a AS a
                        FROM s_terms st
                        JOIN clo sc ON sc.t = st.t
                        JOIN o_clo oc ON oc.a = sc.a
                        WHERE st.batch = ?
                    ),
                    agg AS (  -- ancestors without IC are ignored for Resnik (NULL drops out of max)
                        SELECT c.s, c.o, count(*) AS inter, max(ic.ic) AS resnik
                        FROM common c LEFT JOIN ic ON ic.term = c.a
                        GROUP BY c.s, c.o
                        HAVING max(ic.ic) > ?
                    ),
                    mica AS (  -- the max-IC shared ancestor; ties -> smallest id
                        SELECT c.s, c.o, min(c.a) AS mica
                        FROM common c JOIN ic ON ic.term = c.a
                        JOIN agg g ON g.s = c.s AND g.o = c.o AND ic.ic = g.resnik
                        GROUP BY c.s, c.o
                    )
                    SELECT g.s, g.o, m.mica, g.resnik,
                           g.inter::DOUBLE / (zs.sz + zo.sz - g.inter),
                           sqrt(g.resnik * (g.inter::DOUBLE / (zs.sz + zo.sz - g.inter)))
                    FROM agg g
                    JOIN mica m ON m.s = g.s AND m.o = g.o
                    JOIN sz zs ON zs.t = g.s
                    JOIN sz zo ON zo.t = g.o
                """, [b, config.min_ancestor_information_content])
                if not config.quiet and (b % 10 == 0 or b == n_batches - 1):
                    logger.info(f"pairwise-similarity: batch {b + 1}/{n_batches}")

            if config.labels_table:
                lt = f"kg.{config.labels_table}"
                lid, lname = config.labels_id_column, config.labels_name_column
                select = f"""
                    SELECT r.subject_id, ls.{lname} AS subject_label, r.object_id, lo.{lname} AS object_label,
                           r.ancestor_id, la.{lname} AS ancestor_label,
                           r.ancestor_information_content, r.jaccard_similarity, r.phenodigm_score
                    FROM result r
                    LEFT JOIN {lt} ls ON ls.{lid} = r.subject_id
                    LEFT JOIN {lt} lo ON lo.{lid} = r.object_id
                    LEFT JOIN {lt} la ON la.{lid} = r.ancestor_id"""
            else:
                select = "SELECT * FROM result"
            con.execute(f"COPY ({select}) TO {sql_string_list([str(out)])} {_copy_options(out)}")
            row_count = con.execute("SELECT count(*) FROM result").fetchone()[0]
        finally:
            con.close()
            for f in (work_db, Path(str(work_db) + ".wal")):
                f.unlink(missing_ok=True)

    except Exception as e:
        if not config.quiet:
            print_operation_summary(OperationSummary(
                operation="PairwiseSimilarity", success=False, message=f"Operation failed: {e}",
                files_processed=0, total_time_seconds=time.time() - start_time, errors=[str(e)],
            ))
        raise

    total_time = time.time() - start_time
    summary = OperationSummary(
        operation="PairwiseSimilarity",
        success=True,
        message=(f"Wrote {row_count:,} pairs ({subject_count:,} x {object_count:,} terms) "
                 f"to {out} in {total_time:.2f}s"),
        files_processed=0,
        total_time_seconds=total_time,
        errors=[],
    )
    if not config.quiet:
        print_operation_summary(summary)
    return PairwiseSimilarityResult(
        success=True, output_path=out, subject_count=subject_count, object_count=object_count,
        row_count=row_count, total_time_seconds=total_time, summary=summary,
    )
