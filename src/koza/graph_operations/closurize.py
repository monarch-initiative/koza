"""Closurize operation: produce denormalized_nodes / denormalized_edges by
applying a relation-graph closure to a koza-built DuckDB.

Wraps the SQL engine in `_closurize_engine` and integrates with the graph
schema seam: after closurize finishes, the stored schema in `_koza_schema`
gains `DenormalizedEntity` and `DenormalizedAssociation` classes whose slot
lists come from the actual columns of the produced views.

See decisions/0002-schema-lives-with-database.md and CONTEXT.md.
"""

from __future__ import annotations

import time

from linkml_runtime.linkml_model.meta import ClassDefinition, SlotDefinition
from loguru import logger

from koza.model.graph_operations import (
    ClosurizeConfig,
    ClosurizeResult,
    OperationSummary,
)

from ._closurize_engine import add_closure
from .graph_schema import current_schema, is_seeded, update_schema
from .utils import GraphDatabase, print_operation_summary


# Slots closurize emits regardless of input config. Per-edge derived columns
# materialize onto `edges` itself; the rest land on the denormalized views.
_INVARIANT_ASSOCIATION_SLOTS = ("evidence_count", "grouping_key")
_INVARIANT_ENTITY_SLOTS = (
    "has_descendant",
    "has_descendant_label",
    "has_descendant_count",
)


def closurize_graph(config: ClosurizeConfig) -> ClosurizeResult:
    """Apply closure expansion to a merged graph database.

    Calls the SQL engine in `_closurize_engine` with the configured field
    lists, then evolves the stored `_koza_schema` to include
    `DenormalizedEntity` and `DenormalizedAssociation` classes reflecting
    the actual produced shape.
    """
    start_time = time.time()
    errors: list[str] = []

    try:
        add_closure(
            database_path=str(config.database_path),
            closure_file=str(config.closure_file),
            edge_fields=list(config.edge_fields),
            edge_fields_to_label=list(config.edge_fields_to_label),
            node_fields=list(config.node_fields),
            evidence_fields=list(config.evidence_fields),
            grouping_fields=list(config.grouping_fields),
            additional_node_constraints=config.additional_node_constraints,
        )
        # Note: closurize_graph mutates the stored schema. The
        # DenormalizedEntity/Association classes are rebuilt from current
        # view columns each run, but schema.slots accumulates slot
        # definitions across runs (orphans for slots no longer in any
        # view). Slot definitions are cheap and harmless; the classes
        # remain accurate.

        with GraphDatabase(config.database_path) as db:
            _evolve_schema_for_denormalized(db.conn)
            nodes_count = db.conn.execute(
                "SELECT COUNT(*) FROM denormalized_nodes"
            ).fetchone()[0]
            edges_count = db.conn.execute(
                "SELECT COUNT(*) FROM denormalized_edges"
            ).fetchone()[0]

    except Exception as e:
        total_time = time.time() - start_time
        if not config.quiet:
            summary = OperationSummary(
                operation="Closurize",
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
        operation="Closurize",
        success=True,
        message=(
            f"Denormalized {nodes_count:,} nodes and {edges_count:,} edges "
            f"in {total_time:.2f}s"
        ),
        files_processed=0,
        total_time_seconds=total_time,
        errors=errors,
    )
    if not config.quiet:
        print_operation_summary(summary)

    return ClosurizeResult(
        success=True,
        denormalized_nodes_count=nodes_count,
        denormalized_edges_count=edges_count,
        total_time_seconds=total_time,
        summary=summary,
        errors=errors,
    )


def _evolve_schema_for_denormalized(conn) -> None:
    """If the database is seeded, add DenormalizedEntity / DenormalizedAssociation
    classes to the stored schema. Slot lists come from the actual columns of
    the produced denormalized_nodes / denormalized_edges views.

    Tolerant: if the database is unseeded (no `_koza_schema` table), this is
    a no-op — matching `ensure_slots`' graceful-degradation contract.

    Note: re-running closurize with a different `node_fields` config can leave
    orphan SlotDefinitions in `schema.slots` from a prior run. The class
    `slots:` list is always rebuilt from current view columns, so the
    denormalized classes are correct; only the slot-definition catalog grows.
    """
    if not is_seeded(conn):
        logger.debug("Skipping schema evolution: database is not seeded")
        return

    schema = current_schema(conn)
    de_cols = [r[0] for r in conn.execute("DESCRIBE denormalized_nodes").fetchall()]
    da_cols = [r[0] for r in conn.execute("DESCRIBE denormalized_edges").fetchall()]

    for slot_name in de_cols + da_cols:
        schema.slots.setdefault(slot_name, SlotDefinition(name=slot_name))

    schema.classes["DenormalizedEntity"] = ClassDefinition(
        name="DenormalizedEntity",
        is_a="Entity",
        description="Post-closurize node shape (entity + closure expansion + per-predicate aggregations).",
        slots=de_cols,
    )
    schema.classes["DenormalizedAssociation"] = ClassDefinition(
        name="DenormalizedAssociation",
        is_a="Association",
        description="Post-closurize edge shape (association + subject/object closure expansion).",
        slots=da_cols,
    )

    update_schema(conn, schema)
