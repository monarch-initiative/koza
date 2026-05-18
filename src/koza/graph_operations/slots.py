"""Slot registry — string constants for SQL construction.

Operations import `edges` and `nodes` from this module and reference slots as
attributes (`edges.file_source`, `nodes.id`). Typos surface as
`AttributeError` rather than as SQL "column not found" errors at execution
time.

Hand-written for now. A follow-up will generate this module from the
stored graph schema in each DuckDB.

Slot names match the snake_case form in the derived schema (the canonical
form throughout koza.graph_operations).
"""

from __future__ import annotations


class _NodeSlots:
    id = "id"
    category = "category"
    name = "name"
    description = "description"
    provided_by = "provided_by"
    in_taxon = "in_taxon"
    file_source = "file_source"


class _EdgeSlots:
    subject = "subject"
    predicate = "predicate"
    object = "object"
    category = "category"
    provided_by = "provided_by"
    original_subject = "original_subject"
    original_predicate = "original_predicate"
    original_object = "original_object"
    file_source = "file_source"


nodes = _NodeSlots()
edges = _EdgeSlots()
