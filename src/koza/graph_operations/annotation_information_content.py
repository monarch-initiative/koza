"""Annotation-information-content operation: information content with the
annotated entities as the corpus, over a closurized graph database.

Where `information-content` measures how specific a term is within the ontology
(its corpus is the closure), this measures how specific a term is among the
entities annotated with it -- oaklib's `information-content --use-associations`,
the IC semsimian is given for phenotype comparisons:

    IC(t) = -log2(n(t) / N)

n(t) is the number of distinct entities with an association to t or to any
closure descendant of t (every term counts as its own descendant, whether or not
the closure carries reflexive rows); N is the number of distinct entities with
any selected association. Associations are the `edges` rows matching the configured
predicate, categories, subject/object CURIE prefixes and negation filter, so one
run covers one annotation corpus (e.g. mouse genes -> MP terms). It writes either
its own (term, ic) table or, with `corpus` set, its rows of a (corpus, term, ic)
table several corpora share.

Reproduces oaklib exactly on Monarch's mouse (MGI -> MP) and zebrafish
(ZFIN -> ZP) gene-phenotype corpora. oaklib additionally emits IC 0 rows for a
handful of terms no association reaches; those are not produced here.

Reads `closure` (run `closurize` first) and `edges`; writes only `output_table`,
replacing it if present, or only this corpus's rows of it when `corpus` is set.
"""

from __future__ import annotations

import time

from loguru import logger

from koza.model.graph_operations import (
    AnnotationInformationContentConfig,
    AnnotationInformationContentResult,
    OperationSummary,
)

from .utils import (
    SHARED_IC_COLUMNS,
    GraphDatabase,
    category_membership_filter,
    check_shared_ic_table,
    curie_prefix_filter,
    print_operation_summary,
    sql_string_list,
    table_columns,
)


def _prepare_shared_table(conn, table: str) -> None:
    """Create the shared (corpus, term, ic) table, or check an existing one has its columns."""
    columns = table_columns(conn, table)
    if not columns:
        conn.execute(f"CREATE TABLE {table} ({', '.join(f'{c} {t}' for c, t in SHARED_IC_COLUMNS.items())})")
    elif "corpus" not in columns:
        raise ValueError(f"{table} has no corpus column; it can't hold several corpora")
    else:
        check_shared_ic_table(table, columns)


def compute_annotation_information_content(
    config: AnnotationInformationContentConfig,
) -> AnnotationInformationContentResult:
    """Write `config.output_table` (term, ic), or this corpus's rows of a shared
    (corpus, term, ic) table, to a closurized graph database."""
    start_time = time.time()
    subj, obj = config.association_subject_column, config.association_object_column
    negated_filter = (
        ""
        if config.include_negated
        else " AND (negated IS NULL OR lower(CAST(negated AS VARCHAR)) = 'false')"
    )

    try:
        with GraphDatabase(config.database_path) as db:
            conn = db.conn
            logger.info(
                f"annotation-information-content: database={config.database_path}, "
                f"output_table={config.output_table}, corpus={config.corpus}, "
                f"categories={config.association_categories}, "
                f"subject_prefixes={config.subject_prefixes}, object_prefixes={config.object_prefixes}"
            )
            category_filter = category_membership_filter(
                conn, config.edges_table, config.association_categories
            )
            conn.execute(f"""
                CREATE OR REPLACE TEMP TABLE _annotation_corpus AS
                SELECT DISTINCT {subj} AS entity, {obj} AS term
                FROM {config.edges_table}
                WHERE predicate = {sql_string_list([config.association_predicate])}
                  AND {category_filter}{negated_filter}
                  {curie_prefix_filter(subj, config.subject_prefixes)}
                  {curie_prefix_filter(obj, config.object_prefixes)}
            """)
            entity_count, association_count = conn.execute(
                "SELECT count(DISTINCT entity), count(*) FROM _annotation_corpus"
            ).fetchone()

            # Every annotated term is its own ancestor. Add those self-rows rather
            # than trusting the closure to carry them: without them a term's direct
            # annotations never count toward its own IC and leaf terms get no row.
            # log2(N / n) rather than -log2(n / N), which yields -0.0 when n = N.
            ic_query = f"""
                WITH n AS (SELECT count(DISTINCT entity) AS nn FROM _annotation_corpus),
                clo AS (
                    SELECT {config.closure_subject_column} AS s, {config.closure_object_column} AS o
                    FROM {config.closure_table}
                    WHERE {config.closure_predicate_column} IN ({sql_string_list(config.closure_predicates)})
                    UNION
                    SELECT DISTINCT term, term FROM _annotation_corpus
                )
                SELECT c.o AS term,
                       log2((SELECT nn FROM n)::DOUBLE / count(DISTINCT a.entity)) AS ic
                FROM _annotation_corpus a
                JOIN clo c ON c.s = a.term
                GROUP BY c.o
            """
            if config.corpus is None:
                # Replacing a shared table with one corpus's (term, ic) would silently drop every corpus.
                if "corpus" in table_columns(conn, config.output_table):
                    raise ValueError(
                        f"{config.output_table} holds several corpora (it has a corpus column); "
                        "set corpus to replace one of them"
                    )
                conn.execute(f"CREATE OR REPLACE TABLE {config.output_table} AS {ic_query}")
                term_count = conn.execute(f"SELECT count(*) FROM {config.output_table}").fetchone()[0]
            else:
                # Replace this corpus's rows in one transaction, so readers never see it half-written.
                conn.execute("BEGIN TRANSACTION")
                try:
                    _prepare_shared_table(conn, config.output_table)
                    conn.execute(f"DELETE FROM {config.output_table} WHERE corpus = ?", [config.corpus])
                    conn.execute(
                        f"INSERT INTO {config.output_table} (corpus, term, ic) "
                        f"SELECT ?, term, ic FROM ({ic_query})",
                        [config.corpus],
                    )
                    conn.execute("COMMIT")
                except Exception:
                    conn.execute("ROLLBACK")
                    raise
                term_count = conn.execute(
                    f"SELECT count(*) FROM {config.output_table} WHERE corpus = ?", [config.corpus]
                ).fetchone()[0]
            conn.execute("DROP TABLE _annotation_corpus")

    except Exception as e:
        if not config.quiet:
            print_operation_summary(OperationSummary(
                operation="AnnotationInformationContent",
                success=False,
                message=f"Operation failed: {e}",
                files_processed=0,
                total_time_seconds=time.time() - start_time,
                errors=[str(e)],
            ))
        raise

    total_time = time.time() - start_time
    summary = OperationSummary(
        operation="AnnotationInformationContent",
        success=True,
        message=(
            f"Built {config.output_table}{f' corpus {config.corpus}' if config.corpus else ''} "
            f"({term_count:,} terms) from {entity_count:,} entities / "
            f"{association_count:,} associations in {total_time:.2f}s"
        ),
        files_processed=0,
        total_time_seconds=total_time,
        errors=[],
    )
    if not config.quiet:
        print_operation_summary(summary)

    return AnnotationInformationContentResult(
        success=True,
        output_table=config.output_table,
        corpus=config.corpus,
        term_count=term_count,
        entity_count=entity_count,
        association_count=association_count,
        total_time_seconds=total_time,
        summary=summary,
    )
