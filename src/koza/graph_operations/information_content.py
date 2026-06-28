"""Information-content operation: compute the information-content and
closure-size statistics a semantic-similarity engine needs, over a closurized
graph database.

Run *after* `closurize` — it reads the `closure` table closurize materializes
(``subject_id``, ``predicate_id``, ``object_id``) and the `edges` table, and
writes two small tables a downstream similarity engine can read instead of
rebuilding per process:

- ``information_content`` (term, ic): the information content of each closure
  term, ``IC = -log2(freq / N)`` (oaklib's `information-content`).
- ``closure_size`` (entity, size): the number of distinct closure ancestors
  (subsumers) reachable from the terms an entity is associated with — the
  search-time profile-size denominator.

Everything is plain DuckDB SQL against the existing tables; nothing is read from
the Python environment. The operation mutates the database in place and does not
touch the stored graph schema (these are auxiliary tables, like closurize's
``closure_id`` / ``descendants_id`` side tables).

See CONTEXT.md (Information-content) and the similarity engine in monarch-app.
"""

from __future__ import annotations

import time

from loguru import logger

from koza.model.graph_operations import (
    InformationContentConfig,
    InformationContentResult,
    OperationSummary,
)

from .utils import GraphDatabase, print_operation_summary


def _quote_list(values: list[str]) -> str:
    """Render a list of strings as a SQL ``IN`` body, single-quote-escaped."""
    return ", ".join("'" + v.replace("'", "''") + "'" for v in values)


def compute_information_content(config: InformationContentConfig) -> InformationContentResult:
    """Add the ``information_content`` and ``closure_size`` tables to a
    closurized graph database.

    Requires the database to already contain the `closure` table (run
    `closurize` first) and an `edges` table. Both tables are rebuilt with
    ``CREATE OR REPLACE`` so the operation is idempotent.
    """
    start_time = time.time()
    errors: list[str] = []

    preds = _quote_list(config.closure_predicates)
    categories = _quote_list(config.association_categories)
    # Robust negation filter: edges.negated may be BOOLEAN or VARCHAR ('False').
    negated_filter = (
        ""
        if config.include_negated
        else " AND (negated IS NULL OR lower(CAST(negated AS VARCHAR)) = 'false')"
    )

    try:
        with GraphDatabase(config.database_path) as db:
            conn = db.conn

            logger.info(
                f"information-content: database={config.database_path}, "
                f"closure_predicates={config.closure_predicates}"
            )

            # information_content: IC = -log2(freq / N), freq = #distinct
            # descendants (closure subjects) reaching the term as object, N =
            # #distinct closure objects — over the closure rows whose predicate
            # is in closure_predicates. Count DISTINCT subjects, not rows: with
            # overlapping closure_predicates a descendant can reach the same
            # ancestor via more than one predicate, and counting rows would
            # double-count it (and can push freq past N → negative IC).
            conn.execute(f"""
                CREATE OR REPLACE TABLE information_content AS
                WITH clo AS (
                    SELECT {config.closure_subject_column} AS s,
                           {config.closure_object_column} AS o
                    FROM {config.closure_table}
                    WHERE {config.closure_predicate_column} IN ({preds})
                ),
                n AS (SELECT count(DISTINCT o) AS nn FROM clo)
                SELECT o AS term,
                       -log2(count(DISTINCT s)::DOUBLE / (SELECT nn FROM n)) AS ic
                FROM clo
                GROUP BY o
            """)
            ic_term_count = conn.execute(
                "SELECT count(*) FROM information_content"
            ).fetchone()[0]

            # closure_size: per entity, the number of distinct closure ancestors
            # (subsumers) of the terms it is associated with. `category` may be
            # single-valued (VARCHAR) or multivalued (VARCHAR[] — koza's default
            # for Biolink-multivalued slots), so pick the matching membership
            # test: scalar IN vs list_has_any on the array.
            cat_type = conn.execute(
                "SELECT data_type FROM information_schema.columns "
                f"WHERE table_name = '{config.edges_table}' AND column_name = 'category'"
            ).fetchone()
            if cat_type and cat_type[0].endswith("[]"):
                category_filter = f"list_has_any(category, [{categories}])"
            else:
                category_filter = f"category IN ({categories})"
            conn.execute(f"""
                CREATE OR REPLACE TABLE closure_size AS
                WITH assoc AS (
                    SELECT {config.association_subject_column} AS entity,
                           {config.association_object_column} AS term
                    FROM {config.edges_table}
                    WHERE {category_filter}
                      AND predicate = {_quote_list([config.association_predicate])}{negated_filter}
                ),
                clo AS (
                    SELECT {config.closure_subject_column} AS s,
                           {config.closure_object_column} AS o
                    FROM {config.closure_table}
                    WHERE {config.closure_predicate_column} IN ({preds})
                )
                SELECT a.entity, count(DISTINCT c.o) AS size
                FROM assoc a JOIN clo c ON c.s = a.term
                GROUP BY a.entity
            """)
            closure_size_entity_count = conn.execute(
                "SELECT count(*) FROM closure_size"
            ).fetchone()[0]

    except Exception as e:
        total_time = time.time() - start_time
        if not config.quiet:
            summary = OperationSummary(
                operation="InformationContent",
                success=False,
                message=f"Operation failed: {e}",
                files_processed=0,
                total_time_seconds=total_time,
                errors=[str(e)],
            )
            print_operation_summary(summary)
        raise

    total_time = time.time() - start_time
    summary = OperationSummary(
        operation="InformationContent",
        success=True,
        message=(
            f"Built information_content ({ic_term_count:,} terms) and "
            f"closure_size ({closure_size_entity_count:,} entities) "
            f"in {total_time:.2f}s"
        ),
        files_processed=0,
        total_time_seconds=total_time,
        errors=errors,
    )
    if not config.quiet:
        print_operation_summary(summary)

    return InformationContentResult(
        success=True,
        ic_term_count=ic_term_count,
        closure_size_entity_count=closure_size_entity_count,
        total_time_seconds=total_time,
        summary=summary,
        errors=errors,
    )
