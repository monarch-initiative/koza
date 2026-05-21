"""Graph schema — the seam between operations and the LinkML-derived schema
that lives in each koza-built DuckDB.

See decisions/0001-graph-schema-strict-derivation.md and
decisions/0002-schema-lives-with-database.md.
"""

from __future__ import annotations

import functools
import importlib
import importlib.resources as ir

import duckdb
from linkml_runtime.dumpers import yaml_dumper
from linkml_runtime.linkml_model.meta import (
    ClassDefinition,
    Prefix,
    SchemaDefinition,
    SlotDefinition,
)
from linkml_runtime.loaders import yaml_loader
from linkml_runtime.utils.schemaview import SchemaView


ENTITY_ROOT = "named thing"
ASSOCIATION_ROOT = "association"

_KOZA_SCHEMA_TABLE = "_koza_schema"
_KIND_DERIVED_SCHEMA = "derived_schema"
_KIND_BIOLINK = "biolink"

# Table → schema-class mapping. Driven by the same convention as
# CONTEXT.md: `nodes` ↔ Entity, `edges` ↔ Association. The denormalized_*
# tables join in when closurizer lands in phase 2.
_TABLE_TO_CLASS: dict[str, str] = {
    "nodes": "Entity",
    "edges": "Association",
}

# Operation modules that may export a DECLARED_OUTPUTS constant. Hardcoded
# import list rather than entry-point discovery — koza ships a fixed set of
# operations. Add new operation modules here when they declare outputs.
_OPERATION_MODULES_WITH_OUTPUTS = ("koza.graph_operations.normalize",)


@functools.cache
def load_biolink_schemaview() -> SchemaView:
    """Load the Biolink SchemaView from the pinned biolink-model python
    package. Cached process-wide — Biolink load is ~13s, so this matters."""
    with ir.as_file(ir.files("biolink_model.schema") / "biolink_model.yaml") as p:
        return SchemaView(str(p))


def discover_declared_outputs() -> dict[str, dict[str, dict]]:
    """Union DECLARED_OUTPUTS across all operation modules that export one.

    Returns a dict shaped like `{"Entity": {slot_name: spec, ...}, "Association": {...}}`
    — the shape `derive_schema` expects for its `declared_outputs` kwarg.
    """
    merged: dict[str, dict[str, dict]] = {}
    for module_name in _OPERATION_MODULES_WITH_OUTPUTS:
        module = importlib.import_module(module_name)
        outputs = getattr(module, "DECLARED_OUTPUTS", {})
        for cls_name, slots in outputs.items():
            merged.setdefault(cls_name, {}).update(slots)
    return merged

# Koza ingest-stage extras: slots koza injects at load time that are NOT in
# Biolink. These are added to every class in the derived schema regardless of
# whether they appear in input file headers.
KOZA_INGEST_EXTRAS: dict[str, dict] = {
    "file_source": {
        "description": "Source file stem injected by koza at load time.",
        "range": "string",
        "multivalued": False,
    },
    "provided_by": {
        "description": "Source file stem injected by koza at load time (KGX convention).",
        "range": "string",
        "multivalued": False,
    },
}


class UnknownSlotsError(ValueError):
    """Raised when input file headers contain columns that match no Biolink
    slot and no koza extra. The strict-reject contract from ADR-0001."""


def _snake_case(biolink_name: str) -> str:
    return biolink_name.replace(" ", "_")


def _biolink_slot_pool(sv: SchemaView, root_class: str) -> set[str]:
    """All slots defined on the root class or any descendant, snake_cased.

    Walks `class_slots` only — slots that Biolink defines but doesn't
    attach to any class (e.g. `exact synonym` and other SKOS variants;
    biolink-model issue #1737) won't be here. The permissive `seed_schema`
    path records such columns as opaque slots, surfacing the divergence
    in the stored schema rather than masking it.
    """
    classes = [root_class] + list(sv.class_descendants(root_class))
    names: set[str] = set()
    for c in classes:
        try:
            names.update(sv.class_slots(c))
        except Exception:
            continue
    return {_snake_case(n) for n in names}


def _flatten(
    sv: SchemaView,
    root_class: str,
    headers: list[str],
    class_label: str,
    declared_outputs: dict[str, dict],
) -> tuple[dict[str, SlotDefinition], list[str]]:
    pool = _biolink_slot_pool(sv, root_class)
    slots: dict[str, SlotDefinition] = {}
    rejected: list[str] = []
    for col in headers:
        if col in pool:
            slots[col] = SlotDefinition(name=col)
        elif col in declared_outputs:
            slots[col] = SlotDefinition(name=col, **declared_outputs[col])
        elif col in KOZA_INGEST_EXTRAS:
            # File header includes a koza extra (e.g. file_source). Honor it
            # — the slot is still injected unconditionally by
            # `_with_ingest_extras`, but presence in headers must not trip
            # strict-reject.
            slots[col] = SlotDefinition(name=col, **KOZA_INGEST_EXTRAS[col])
        else:
            rejected.append(col)
    for name, spec in declared_outputs.items():
        slots.setdefault(name, SlotDefinition(name=name, **spec))
    return slots, rejected


def _with_ingest_extras(slots: dict[str, SlotDefinition]) -> dict[str, SlotDefinition]:
    merged: dict[str, SlotDefinition] = {}
    for name, spec in KOZA_INGEST_EXTRAS.items():
        merged[name] = SlotDefinition(name=name, **spec)
    merged.update(slots)
    return merged


def derive_schema(
    nodes_headers: list[str],
    edges_headers: list[str],
    biolink_schemaview: SchemaView,
    declared_outputs: dict[str, dict[str, dict]] | None = None,
    strict: bool = True,
) -> SchemaDefinition:
    """Derive a flat LinkML schema from input file headers + Biolink.

    With `strict=True` (default), columns that match no Biolink slot, no
    koza extra, and no declared output raise UnknownSlotsError — the
    contract from ADR-0001.

    With `strict=False`, unknown columns are added as minimal VARCHAR
    slots so the resulting schema reflects whatever's in the data. Used
    by `seed_schema` to record the schema of an already-loaded graph
    rather than enforce validation against it.
    """
    declared_outputs = declared_outputs or {}
    entity_outputs = declared_outputs.get("Entity", {})
    association_outputs = declared_outputs.get("Association", {})

    entity_slots, entity_rejected = _flatten(
        biolink_schemaview, ENTITY_ROOT, nodes_headers, "Entity", entity_outputs
    )
    association_slots, association_rejected = _flatten(
        biolink_schemaview,
        ASSOCIATION_ROOT,
        edges_headers,
        "Association",
        association_outputs,
    )
    entity_slots = _with_ingest_extras(entity_slots)
    association_slots = _with_ingest_extras(association_slots)

    rejected = [(c, "Entity") for c in entity_rejected] + [
        (c, "Association") for c in association_rejected
    ]
    if rejected:
        if strict:
            details = ", ".join(f"{col} (in {cls})" for col, cls in rejected)
            raise UnknownSlotsError(
                f"Input headers contain {len(rejected)} column(s) that match no "
                f"Biolink slot and no koza extra: {details}"
            )
        # Permissive: record unknowns as minimal slots so the schema
        # reflects what's actually in the database.
        for col, cls in rejected:
            target = entity_slots if cls == "Entity" else association_slots
            target.setdefault(col, SlotDefinition(name=col))

    schema = SchemaDefinition(
        id="https://w3id.org/monarch-initiative/koza/graph-schema",
        name="koza-graph-schema",
    )
    schema.slots = {**entity_slots, **association_slots}
    schema.classes = {
        "Entity": ClassDefinition(name="Entity", slots=list(entity_slots.keys())),
        "Association": ClassDefinition(
            name="Association", slots=list(association_slots.keys())
        ),
    }
    return schema


def _ensure_metadata_table(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {_KOZA_SCHEMA_TABLE} "
        f"(kind VARCHAR PRIMARY KEY, content VARCHAR)"
    )


def _write_metadata(
    conn: duckdb.DuckDBPyConnection, kind: str, content: str
) -> None:
    conn.execute(
        f"INSERT OR REPLACE INTO {_KOZA_SCHEMA_TABLE} (kind, content) VALUES (?, ?)",
        [kind, content],
    )


def _read_metadata(conn: duckdb.DuckDBPyConnection, kind: str) -> str | None:
    try:
        row = conn.execute(
            f"SELECT content FROM {_KOZA_SCHEMA_TABLE} WHERE kind = ?", [kind]
        ).fetchone()
    except duckdb.CatalogException:
        # Table doesn't exist — DB predates the schema feature.
        return None
    return row[0] if row else None


def seed_schema(
    conn: duckdb.DuckDBPyConnection,
    nodes_headers: list[str],
    edges_headers: list[str],
    biolink_schemaview: SchemaView,
    declared_outputs: dict[str, dict[str, dict]] | None = None,
) -> SchemaDefinition:
    """Derive a graph schema and persist it as metadata in the DuckDB.

    Called once at graph creation. After this, operations read and evolve the
    stored schema rather than re-deriving from Biolink.
    """
    # Permissive — the data already exists; the schema should reflect it.
    # Strict-reject is for future load/append validation through the seam.
    schema = derive_schema(
        nodes_headers=nodes_headers,
        edges_headers=edges_headers,
        biolink_schemaview=biolink_schemaview,
        declared_outputs=declared_outputs,
        strict=False,
    )
    _ensure_metadata_table(conn)
    _write_metadata(conn, _KIND_DERIVED_SCHEMA, yaml_dumper.dumps(schema))
    _write_metadata(
        conn, _KIND_BIOLINK, yaml_dumper.dumps(biolink_schemaview.schema)
    )
    return schema


def current_schema(conn: duckdb.DuckDBPyConnection) -> SchemaDefinition:
    """Read the stored graph schema from this DuckDB's metadata."""
    content = _read_metadata(conn, _KIND_DERIVED_SCHEMA)
    if content is None:
        raise RuntimeError(
            f"No graph schema found in {_KOZA_SCHEMA_TABLE} — was seed_schema called?"
        )
    return yaml_loader.loads(content, target_class=SchemaDefinition)


def export_schema(
    conn: duckdb.DuckDBPyConnection,
    project_denormalized: bool = True,
) -> str:
    """Export the stored graph schema as a YAML string suitable for release.

    With `project_denormalized=True` (default), `DenormalizedEntity` and
    `DenormalizedAssociation` are renamed to `Entity` / `Association` and the
    narrow post-merge classes are dropped — matching monarch-app's convention
    where those names refer to the post-closurize wide shape.

    Slot definitions are enriched with `multivalued: true` for any slot whose
    column in `denormalized_nodes` or `denormalized_edges` is `VARCHAR[]`.
    """
    schema = current_schema(conn)

    # Released schema must be standalone-loadable by linkml tooling: linkml:types
    # is needed for `range: string` etc. to resolve, and the prefixes need to be
    # declared for CURIE expansion.
    if "linkml:types" not in (schema.imports or []):
        schema.imports = list(schema.imports or []) + ["linkml:types"]
    if not schema.default_range:
        schema.default_range = "string"
    prefixes = dict(schema.prefixes or {})
    for prefix, uri in (
        ("linkml", "https://w3id.org/linkml/"),
        ("biolink", "https://w3id.org/biolink/vocab/"),
    ):
        prefixes.setdefault(prefix, Prefix(prefix_prefix=prefix, prefix_reference=uri))
    schema.prefixes = prefixes

    if project_denormalized:
        new_classes: dict[str, ClassDefinition] = {}
        rename = {"DenormalizedEntity": "Entity", "DenormalizedAssociation": "Association"}
        for cls_name, cls_def in schema.classes.items():
            target = rename.get(cls_name)
            if target is None:
                # Drop narrow post-merge classes when we're projecting denorm names
                if cls_name in ("Entity", "Association"):
                    continue
                new_classes[cls_name] = cls_def
            else:
                cls_def.name = target
                cls_def.is_a = None  # parent class is being dropped
                new_classes[target] = cls_def
        schema.classes = new_classes

    # Derive multivalued from actual DuckDB column types of the denormalized views.
    multivalued_slots: set[str] = set()
    for table in ("denormalized_nodes", "denormalized_edges"):
        try:
            rows = conn.execute(f"DESCRIBE {table}").fetchall()
        except duckdb.CatalogException:
            # Pre-closurize DB; just skip — the schema is still exportable
            # with whatever Entity / Association slot info we have.
            continue
        for col_name, col_type, *_ in rows:
            if "VARCHAR[]" in (col_type or "").upper():
                multivalued_slots.add(col_name)

    for slot_name in multivalued_slots:
        slot = schema.slots.get(slot_name)
        if slot is None:
            slot = SlotDefinition(name=slot_name)
            schema.slots[slot_name] = slot
        slot.multivalued = True

    return yaml_dumper.dumps(schema)


def is_seeded(conn: duckdb.DuckDBPyConnection) -> bool:
    """Whether this DuckDB has a stored graph schema (the `_koza_schema`
    metadata table with a derived_schema row). False for graphs from before
    the schema feature existed or for fresh DuckDBs that haven't been
    through `seed_schema` yet."""
    return _read_metadata(conn, _KIND_DERIVED_SCHEMA) is not None


def update_schema(conn: duckdb.DuckDBPyConnection, schema: SchemaDefinition) -> None:
    """Persist `schema` as the stored derived schema for this DuckDB.

    Used by operations that evolve the schema after seed time (e.g.
    `ensure_slots` adds materialized slot columns; `closurize_graph` adds
    `DenormalizedEntity` / `DenormalizedAssociation` classes). Requires
    the database to already be seeded — call `is_seeded(conn)` first.
    """
    _write_metadata(conn, _KIND_DERIVED_SCHEMA, yaml_dumper.dumps(schema))


def stored_biolink_yaml(conn: duckdb.DuckDBPyConnection) -> str | None:
    """Read the Biolink YAML stored at seed time. Routine operations should
    not need this — the derived schema is the operation-facing contract.
    Used by `koza schema rebase` to diff stored vs. fresh Biolink."""
    return _read_metadata(conn, _KIND_BIOLINK)


def _duckdb_type_for(slot_def: SlotDefinition | None) -> str:
    if slot_def is not None and slot_def.multivalued:
        return "VARCHAR[]"
    return "VARCHAR"


def ensure_slots(
    conn: duckdb.DuckDBPyConnection, table: str, slot_names: list[str]
) -> None:
    """Make sure `table` has columns for each slot in `slot_names`, ALTERing
    as needed. Idempotent: slots already present as columns are skipped.

    Called by operations before they write columns they declared via
    DECLARED_OUTPUTS. If the DuckDB has a seeded schema, this also keeps the
    stored schema in sync (adding the slot to the relevant class). On an
    unseeded DB it gracefully degrades to a plain ALTER TABLE so operations
    still work on graphs that predate the schema feature; the column type
    falls back to VARCHAR since multivalued-ness is unknown without a schema.
    """
    if table not in _TABLE_TO_CLASS:
        raise ValueError(
            f"Unknown table {table!r} — known tables: {sorted(_TABLE_TO_CLASS)}"
        )

    try:
        schema: SchemaDefinition | None = current_schema(conn)
    except RuntimeError:
        schema = None

    existing_cols = {r[0] for r in conn.execute(f"DESCRIBE {table}").fetchall()}
    schema_dirty = False
    for slot in slot_names:
        if slot not in existing_cols:
            slot_def = schema.slots.get(slot) if schema is not None else None
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN {slot} {_duckdb_type_for(slot_def)}"
            )
        if schema is not None:
            class_def = schema.classes[_TABLE_TO_CLASS[table]]
            if slot not in class_def.slots:
                class_def.slots.append(slot)
                schema_dirty = True

    if schema is not None and schema_dirty:
        _write_metadata(conn, _KIND_DERIVED_SCHEMA, yaml_dumper.dumps(schema))
