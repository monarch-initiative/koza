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
run covers one annotation corpus (e.g. mouse genes -> MP terms) and writes it to
its own table.

Reproduces oaklib exactly on Monarch's mouse (MGI -> MP) and zebrafish
(ZFIN -> ZP) gene-phenotype corpora. oaklib additionally emits IC 0 rows for a
handful of terms no association reaches; those are not produced here.

Reads `closure` (run `closurize` first) and `edges`; writes only `output_table`,
replacing it if present.
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
    GraphDatabase,
    category_membership_filter,
    curie_prefix_filter,
    print_operation_summary,
    sql_string_list,
)


def compute_annotation_information_content(
    config: AnnotationInformationContentConfig,
) -> AnnotationInformationContentResult:
    """Write `config.output_table` (term, ic) to a closurized graph database."""
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
                f"output_table={config.output_table}, categories={config.association_categories}, "
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
            conn.execute(f"""
                CREATE OR REPLACE TABLE {config.output_table} AS
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
            """)
            conn.execute("DROP TABLE _annotation_corpus")
            term_count = conn.execute(f"SELECT count(*) FROM {config.output_table}").fetchone()[0]

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
            f"Built {config.output_table} ({term_count:,} terms) from {entity_count:,} entities / "
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
        term_count=term_count,
        entity_count=entity_count,
        association_count=association_count,
        total_time_seconds=total_time,
        summary=summary,
    )
