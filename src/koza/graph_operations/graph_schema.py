"""Graph schema — the seam between operations and the LinkML-derived schema
that lives in each koza-built DuckDB.

See decisions/0001-graph-schema-strict-derivation.md and
decisions/0002-schema-lives-with-database.md.
"""

from __future__ import annotations

import functools
import importlib
import importlib.resources as ir
from pathlib import Path

import duckdb
import yaml
from linkml_runtime.dumpers import yaml_dumper
from linkml_runtime.linkml_model.meta import (
    ClassDefinition,
    Prefix,
    SchemaDefinition,
    SlotDefinition,
)
from linkml_runtime.loaders import yaml_loader
from linkml_runtime.utils.formatutils import camelcase
from linkml_runtime.utils.schema_as_dict import schema_as_dict
from linkml_runtime.utils.schemaview import SchemaView
from loguru import logger


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

# Slots that lead a class, in this order, when the class has them; everything
# else follows alphabetically. Slot order reaches users as column order in the
# CLI's table and TSV output, so a plain alphabetical sort would lead `Entity`
# with `broad_synonym` and bury `id`.
_LEAD_SLOTS: tuple[str, ...] = (
    "id",
    "category",
    "subject",
    "predicate",
    "object",
    "name",
    "full_name",
    "symbol",
    "description",
)


def _canonical_slot_order(slots: list[str]) -> list[str]:
    """Identity slots first in `_LEAD_SLOTS` order, then the rest alphabetically."""
    lead = [slot for slot in _LEAD_SLOTS if slot in slots]
    return lead + sorted(set(slots) - set(lead))


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


# LinkML built-in scalar types that downstream LinkML tooling resolves without
# a Biolink import. The released schema only imports `linkml:types`, so every
# slot range it emits must reduce to one of these to stay standalone-loadable
# (ADR-0002). `uriorcurie`/`uri` are kept (they carry identifier intent and
# tools collapse them to a string field); anything else falls back to `string`.
_LINKML_BUILTIN_PRIMITIVES: frozenset[str] = frozenset(
    {
        "string",
        "integer",
        "boolean",
        "float",
        "double",
        "decimal",
        "date",
        "datetime",
        "time",
        "uriorcurie",
        "uri",
    }
)


def _primitive_range(sv: SchemaView, range_name: str | None) -> str | None:
    """Reduce a Biolink range to a standalone-resolvable LinkML primitive.

    The released schema (see `export_schema`) imports only `linkml:types`, so a
    range that names a Biolink class, enum, or type would be a dangling
    reference — linkml-solr's `create-schema` and other LinkML tooling reject
    it. We resolve here, at derive time, where the Biolink SchemaView is in hand
    (ADR-0002 keeps export from re-loading Biolink):

    - class-valued slot  → ``uriorcurie`` (the column holds a CURIE reference)
    - enum-valued slot   → ``string`` (permissible values serialize as strings)
    - type-valued slot   → walk the ``typeof`` chain to the underlying built-in

    The resolved primitive is informational only — no operation dispatches on
    the stored range (column types come from the live Biolink SchemaView via
    `duckdb_columns_for_slots`), and Biolink slot identity is preserved on every
    slot through `slot_uri` / `exact_mappings`.
    """
    if range_name is None:
        return None
    if range_name in sv.all_classes():
        return "uriorcurie"
    if range_name in sv.all_enums():
        return "string"
    t = sv.get_type(range_name)
    if t is None:
        # Not a known class/enum/type — leave it for default_range handling.
        return range_name
    seen: set[str] = set()
    while t is not None and t.typeof and t.name not in seen:
        seen.add(t.name)
        t = sv.get_type(t.typeof)
    resolved = t.name if t is not None else range_name
    return resolved if resolved in _LINKML_BUILTIN_PRIMITIVES else "string"


# CURIE prefixes that can appear in exported slot_uri / exact_mappings, with
# their canonical reference URIs. Kept static so export stays standalone and
# does not re-load Biolink (ADR-0002): slot_uri across the Biolink slot pool
# resolves to one of these, and exact_mappings always use `biolink`.
_KNOWN_PREFIX_URIS: dict[str, str] = {
    "linkml": "https://w3id.org/linkml/",
    "biolink": "https://w3id.org/biolink/vocab/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "dct": "http://purl.org/dc/terms/",
    "schema": "http://schema.org/",
}


def _biolink_derived_slot(sv: SchemaView, col: str, root_class: str) -> SlotDefinition:
    """A SlotDefinition for a column that matched the Biolink slot pool,
    carrying semantic references back to the Biolink slot it was derived from.

    `slot_uri` is Biolink's canonical predicate URI for the slot — usually
    `biolink:<name>`, but for some slots Biolink maps it elsewhere (e.g. `name`
    → `rdfs:label`, `subject` → `rdf:subject`). `exact_mappings` pins the
    Biolink slot identity (`biolink:<name>`) regardless, so provenance to the
    originating Biolink slot survives even when slot_uri points away.

    `range` is captured from Biolink here (where the SchemaView is available)
    so it persists in the stored schema and the export doesn't have to reload
    Biolink (ADR-0002) — e.g. `has_count` → integer, `negated` → boolean. It is
    reduced to a standalone-resolvable LinkML primitive via `_primitive_range`
    so the released schema (which imports only `linkml:types`) stays loadable —
    e.g. `name` (Biolink `label type`) → string, `has_gene` (Biolink `gene`)
    → uriorcurie.

    The slot is resolved as one shape across every class under `root_class`
    (see `_column_slot`), so Biolink's class-level `slot_usage` applies.
    `slot_uri` still comes from the global slot — it is the slot's identity,
    not part of its per-class shape.
    """
    biolink_slot = _column_slot(sv, col, root_class)
    slot_range = (
        _primitive_range(sv, biolink_slot.range) if biolink_slot is not None else None
    )
    try:
        global_slot = sv.get_slot(col.replace("_", " "))
        slot_uri = sv.get_uri(global_slot) if global_slot is not None else None
    except Exception:
        logger.warning(f"Could not resolve slot_uri for Biolink slot {col!r}")
        slot_uri = None
    return SlotDefinition(
        name=col, range=slot_range, slot_uri=slot_uri, exact_mappings=[f"biolink:{col}"]
    )


# How deep `_inline_class` follows nested STRUCT fields into further inlined
# classes before leaving a field as a plain primitive.
_MAX_INLINE_DEPTH = 3


def _parse_duckdb_type(col_type: str | None) -> duckdb.typing.DuckDBPyType | None:
    if not col_type:
        return None
    try:
        return duckdb.sqltype(col_type)
    except Exception:
        return None


def _list_element(
    col_type: duckdb.typing.DuckDBPyType,
) -> tuple[duckdb.typing.DuckDBPyType, bool]:
    """Unwrap one list level: ``(element type, True)`` for a LIST or fixed-size
    ARRAY, else ``(type, False)``."""
    if col_type.id in ("list", "array"):
        return col_type.children[0][1], True
    return col_type, False


def _induced_biolink_slot(
    sv: SchemaView, name: str, class_name: str
) -> SlotDefinition | None:
    """The Biolink slot as seen from `class_name`, so class-level `slot_usage`
    applies. Falls back to the global slot when it can't be induced there."""
    biolink_name = name.replace("_", " ")
    try:
        return sv.induced_slot(biolink_name, class_name)
    except Exception:
        return sv.get_slot(biolink_name)


# (id(SchemaView), root class) -> (SchemaView, {biolink slot name: shape}).
# The SchemaView is held so its id can't be reused while the entry lives.
_COLUMN_SLOT_CACHE: dict[tuple[int, str], tuple[SchemaView, dict[str, SlotDefinition]]] = {}

_SHAPE_FLAGS = ("multivalued", "inlined", "inlined_as_list")


def _column_slot(sv: SchemaView, name: str, root_class: str) -> SlotDefinition | None:
    """The single shape of a Biolink slot across a whole column.

    A `nodes` / `edges` column holds rows of every class under `root_class`,
    and Biolink refines slots per class via `slot_usage` — including on
    descendants the slot only appears on (e.g. `association` declares
    `sources` `inlined_as_list`; subclasses narrow `subject` / `object`
    ranges). So the shape is resolved over every class in the hierarchy
    that uses the slot:

    - flags (`multivalued`, `inlined`, `inlined_as_list`): the value all
      those classes agree on; on disagreement, the global slot's value,
      with a warning
    - range: the agreed range; otherwise the broadest — the range induced
      on `root_class` if the slot is used there, else the global slot's
    """
    key = (id(sv), root_class)
    cached = _COLUMN_SLOT_CACHE.get(key)
    if cached is None or cached[0] is not sv:
        cached = (sv, _column_slot_shapes(sv, root_class))
        _COLUMN_SLOT_CACHE[key] = cached
    return cached[1].get(name.replace("_", " "))


def _column_slot_shapes(sv: SchemaView, root_class: str) -> dict[str, SlotDefinition]:
    per_slot: dict[str, list[SlotDefinition]] = {}
    for cls in [root_class, *sv.class_descendants(root_class)]:
        try:
            induced = sv.class_induced_slots(cls)
        except Exception:
            continue
        for slot in induced:
            per_slot.setdefault(slot.name, []).append(slot)

    root_slots = set(sv.class_slots(root_class))
    shapes: dict[str, SlotDefinition] = {}
    for name, variants in per_slot.items():
        base = variants[0] if name in root_slots else sv.get_slot(name)
        if base is None:
            base = variants[0]
        shape = SlotDefinition(name=name, range=base.range)
        if len({str(v.range) for v in variants}) == 1:
            shape.range = variants[0].range
        for flag in _SHAPE_FLAGS:
            values = {bool(getattr(v, flag)) for v in variants}
            if len(values) == 1:
                setattr(shape, flag, values.pop() or None)
            else:
                logger.warning(
                    f"Biolink slot {name!r} has conflicting {flag!r} across "
                    f"{root_class!r} descendants; using the global slot's value"
                )
                global_slot = sv.get_slot(name)
                setattr(shape, flag, getattr(global_slot, flag, None) if global_slot else None)
        shapes[name] = shape
    return shapes


def _inline_class(
    sv: SchemaView,
    biolink_class: str,
    struct_type: duckdb.typing.DuckDBPyType,
    classes: dict[str, ClassDefinition],
    depth: int = 0,
) -> str:
    """Record a standalone definition of `biolink_class` shaped by the fields of
    a STRUCT column, and return its class name.

    Attributes come from the struct's fields, not Biolink's full induced slot
    list, so the class describes what the data actually holds. Ranges reduce
    via `_primitive_range` like top-level slots, keeping the released schema
    loadable with only `linkml:types` (ADR-0002). A class reached from several
    columns accumulates the union of their fields, each widened to cover every
    column it appears in (see `_merge_slot_shape`).
    """
    name = camelcase(biolink_class)
    class_def = classes.get(name)
    if class_def is None:
        class_def = ClassDefinition(
            name=name, class_uri=sv.get_uri(sv.get_class(biolink_class))
        )
        classes[name] = class_def
    for field, field_type in struct_type.children:
        element, is_list = _list_element(field_type)
        biolink_slot = _induced_biolink_slot(sv, field, biolink_class)
        attr = SlotDefinition(name=field)
        if biolink_slot is not None:
            attr.exact_mappings = [f"biolink:{field}"]
        if (
            element.id == "struct"
            and biolink_slot is not None
            and biolink_slot.range in sv.all_classes()
            and depth < _MAX_INLINE_DEPTH
        ):
            attr.range = _inline_class(sv, biolink_slot.range, element, classes, depth + 1)
            attr.inlined = True
            if is_list:
                attr.inlined_as_list = True
        elif biolink_slot is not None:
            attr.range = _primitive_range(sv, biolink_slot.range)
        else:
            # Non-Biolink field: range from its DuckDB type. VARCHAR is recorded as
            # `string` (not left unset) so a typed field elsewhere can't silently
            # narrow it when the class is merged across columns.
            attr.range = "string" if element.id == "varchar" else _DUCKDB_SCALAR_TO_RANGE.get(str(element).upper())
        if is_list:
            attr.multivalued = True
        existing = class_def.attributes.get(field)
        if existing is None:
            class_def.attributes[field] = attr
        else:
            _merge_slot_shape(existing, attr, f"{name}.{field}")
    return name


# How wide a primitive range is when merging two columns' shapes: the wider
# one can hold every value of the narrower.
_RANGE_WIDTH: dict[str, int] = {
    "integer": 1,
    "float": 2,
    "double": 2,
    "decimal": 2,
    "string": 3,
}


def _merge_flag(a, b):
    """True if either flag is true; False if either was explicitly false; else unset."""
    if a or b:
        return True
    if a is False or b is False:
        return False
    return None


def _merge_slot_shape(base: SlotDefinition, other: SlotDefinition, label: str) -> None:
    """Widen `base` in place to also describe `other` — the same slot as seen in
    another column (nodes vs. edges share one flat slot namespace; an inlined
    class can be reached from several columns).

    - `multivalued` / `inlined`: true if either is; an explicit false is kept
      when neither is true
    - a multivalued, inlined slot is always `inlined_as_list` — without it
      LinkML reads multivalued+inlined as a dict keyed by identifier
    - range: an inlined class beats a reference or primitive; between two
      non-inlined primitives the wider wins (`string` > `float`/`double`/
      `decimal` > `integer`), so a column's values always fit the range;
      otherwise `other` wins (matching the previous last-definition-wins
      behavior). Differing ranges are logged.
    """
    if other.range is not None and str(other.range) != str(base.range):
        if base.range is not None:
            logger.warning(
                f"Slot {label!r} has different shapes across columns: range "
                f"{base.range!r} vs {other.range!r}"
            )
        base_width = _RANGE_WIDTH.get(str(base.range))
        other_width = _RANGE_WIDTH.get(str(other.range))
        if base.inlined and not other.inlined:
            pass
        elif not other.inlined and base_width is not None and other_width is not None:
            if other_width > base_width:
                base.range = other.range
        else:
            base.range = other.range
    base.multivalued = _merge_flag(base.multivalued, other.multivalued)
    base.inlined = _merge_flag(base.inlined, other.inlined)
    if base.multivalued and base.inlined:
        base.inlined_as_list = True
    elif not base.inlined:
        base.inlined_as_list = None


def _apply_inline_struct(
    sv: SchemaView,
    slot: SlotDefinition,
    root_class: str,
    col_type: str | None,
    classes: dict[str, ClassDefinition],
) -> None:
    """Declare `slot` as an inlined class when its column holds records.

    `_primitive_range` reduces class-valued Biolink ranges to `uriorcurie`,
    which is right for reference columns. A STRUCT (or STRUCT[]) column holds
    the records themselves, so the slot keeps its Biolink class as range and
    is marked `inlined` (plus `inlined_as_list` for a list) — the shape
    consumers need to serialize it.
    """
    parsed = _parse_duckdb_type(col_type)
    if parsed is None:
        return
    element, is_list = _list_element(parsed)
    if element.id != "struct":
        return
    biolink_slot = _column_slot(sv, slot.name, root_class)
    if biolink_slot is None or biolink_slot.range not in sv.all_classes():
        return
    slot.range = _inline_class(sv, biolink_slot.range, element, classes)
    slot.inlined = True
    if is_list:
        slot.multivalued = True
        slot.inlined_as_list = True


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
    column_types: dict[str, str] | None = None,
    inline_classes: dict[str, ClassDefinition] | None = None,
) -> tuple[dict[str, SlotDefinition], list[str]]:
    pool = _biolink_slot_pool(sv, root_class)
    column_types = column_types or {}
    inline_classes = inline_classes if inline_classes is not None else {}
    slots: dict[str, SlotDefinition] = {}
    rejected: list[str] = []
    for col in headers:
        if col in pool:
            slots[col] = _biolink_derived_slot(sv, col, root_class)
            _apply_inline_struct(
                sv, slots[col], root_class, column_types.get(col), inline_classes
            )
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
    nodes_column_types: dict[str, str] | None = None,
    edges_column_types: dict[str, str] | None = None,
) -> SchemaDefinition:
    """Derive a flat LinkML schema from input file headers + Biolink.

    With `strict=True` (default), columns that match no Biolink slot, no
    koza extra, and no declared output raise UnknownSlotsError — the
    contract from ADR-0001.

    With `strict=False`, unknown columns are added as minimal VARCHAR
    slots so the resulting schema reflects whatever's in the data. Used
    by `seed_schema` to record the schema of an already-loaded graph
    rather than enforce validation against it.

    `nodes_column_types` / `edges_column_types` map column name to DuckDB type.
    When given, a Biolink class-valued slot whose column is a STRUCT (or
    STRUCT[]) is declared as an inlined class rather than a CURIE reference,
    and that class's definition is added to the schema (see
    `_apply_inline_struct`).
    """
    declared_outputs = declared_outputs or {}
    entity_outputs = declared_outputs.get("Entity", {})
    association_outputs = declared_outputs.get("Association", {})
    inline_classes: dict[str, ClassDefinition] = {}

    entity_slots, entity_rejected = _flatten(
        biolink_schemaview,
        ENTITY_ROOT,
        nodes_headers,
        "Entity",
        entity_outputs,
        nodes_column_types,
        inline_classes,
    )
    association_slots, association_rejected = _flatten(
        biolink_schemaview,
        ASSOCIATION_ROOT,
        edges_headers,
        "Association",
        association_outputs,
        edges_column_types,
        inline_classes,
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
    # Nodes and edges share one flat slot namespace; a slot in both gets one
    # shape covering both columns.
    merged_slots = dict(entity_slots)
    for name, slot in association_slots.items():
        if name in merged_slots:
            _merge_slot_shape(merged_slots[name], slot, name)
        else:
            merged_slots[name] = slot
    schema.slots = merged_slots
    schema.classes = {
        "Entity": ClassDefinition(name="Entity", slots=list(entity_slots.keys())),
        "Association": ClassDefinition(
            name="Association", slots=list(association_slots.keys())
        ),
        **inline_classes,
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
    nodes_column_types: dict[str, str] | None = None,
    edges_column_types: dict[str, str] | None = None,
    overlay: dict | None = None,
) -> SchemaDefinition:
    """Derive a graph schema and persist it as metadata in the DuckDB.

    Called once at graph creation. After this, operations read and evolve the
    stored schema rather than re-deriving from Biolink. `overlay`, if given,
    is applied to the derived schema first (see `apply_schema_overlay`).
    """
    # Permissive — the data already exists; the schema should reflect it.
    # Strict-reject is for future load/append validation through the seam.
    schema = derive_schema(
        nodes_headers=nodes_headers,
        edges_headers=edges_headers,
        biolink_schemaview=biolink_schemaview,
        declared_outputs=declared_outputs,
        strict=False,
        nodes_column_types=nodes_column_types,
        edges_column_types=edges_column_types,
    )
    if overlay:
        apply_schema_overlay(
            schema,
            overlay,
            biolink_schemaview,
            column_types={
                "Entity": nodes_column_types or {},
                "Association": edges_column_types or {},
            },
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

    `multivalued` on each slot follows its column in `denormalized_nodes` /
    `denormalized_edges`: true for a LIST type, unset for a scalar.
    """
    schema = current_schema(conn)

    # Released schema must be standalone-loadable by linkml tooling: linkml:types
    # is needed for `range: string` etc. to resolve, and the prefixes need to be
    # declared for CURIE expansion.
    if "linkml:types" not in (schema.imports or []):
        schema.imports = list(schema.imports or []) + ["linkml:types"]
    if not schema.default_range:
        schema.default_range = "string"
    # Declare every prefix the schema actually references — linkml:types plus
    # the prefixes used by the slot_uri / exact_mappings we attach to derived
    # slots — so the released schema is standalone-loadable for CURIE expansion.
    prefixes = dict(schema.prefixes or {})
    used_prefixes = {"linkml", "biolink"}
    references: list[str | None] = []
    for slot in schema.slots.values():
        references += [slot.slot_uri, *(slot.exact_mappings or [])]
    for cls in schema.classes.values():
        references.append(cls.class_uri)
        for attr in (cls.attributes or {}).values():
            references += [attr.slot_uri, *(attr.exact_mappings or [])]
    for curie in references:
        if curie and ":" in curie:
            used_prefixes.add(curie.split(":", 1)[0])
    for prefix in sorted(used_prefixes):
        uri = _KNOWN_PREFIX_URIS.get(prefix)
        if uri is None:
            raise ValueError(
                f"Slot references use CURIE prefix {prefix!r} which has no entry "
                f"in _KNOWN_PREFIX_URIS — the exported schema would not be "
                f"standalone-loadable. Add its reference URI to _KNOWN_PREFIX_URIS."
            )
        prefixes.setdefault(
            prefix, Prefix(prefix_prefix=prefix, prefix_reference=uri)
        )
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

    # Derive multivalued + scalar range from actual DuckDB column types of the
    # denormalized views.
    multivalued_slots: set[str] = set()
    scalar_types: dict[str, str] = {}
    for table in ("denormalized_nodes", "denormalized_edges"):
        try:
            rows = conn.execute(f"DESCRIBE {table}").fetchall()
        except duckdb.CatalogException:
            # Pre-closurize DB; just skip — the schema is still exportable
            # with whatever Entity / Association slot info we have.
            continue
        for col_name, col_type, *_ in rows:
            parsed = _parse_duckdb_type(col_type)
            if parsed is None:
                scalar_types[col_name] = (col_type or "").upper()
                continue
            # The outer type decides: `STRUCT(x VARCHAR[])` is one record, not a list.
            if _list_element(parsed)[1]:
                multivalued_slots.add(col_name)
            else:
                scalar_types[col_name] = (col_type or "").upper()

    for slot_name in multivalued_slots:
        slot = schema.slots.get(slot_name)
        if slot is None:
            slot = SlotDefinition(name=slot_name)
            schema.slots[slot_name] = slot
        slot.multivalued = True
        # Seeded single-valued but a list here (e.g. a STRUCT on one table, a
        # list on the other): inlined records must still be a list, not a dict.
        if slot.inlined:
            slot.inlined_as_list = True

    # The column type wins in the other direction too: a slot Biolink declares
    # multivalued but the build stores as a scalar (e.g. `in_taxon` under
    # `force_single_valued`) is single-valued in this graph.
    for slot_name in scalar_types:
        slot = schema.slots.get(slot_name)
        if slot is not None and slot.multivalued and slot_name not in multivalued_slots:
            slot.multivalued = None
            slot.inlined_as_list = None

    # Recover range for computed, non-Biolink scalar columns from their DuckDB
    # type — only where the slot has no range yet, so Biolink-derived ranges
    # (captured at derive time) win over the lossy DuckDB inverse.
    for slot_name, col_type in scalar_types.items():
        slot = schema.slots.get(slot_name)
        if slot is None or slot.range:
            continue
        rng = _DUCKDB_SCALAR_TO_RANGE.get(col_type)
        if rng:
            slot.range = rng


    # schema_as_dict emits the idiomatic compact schema form — `prefix: uri`
    # rather than expanded Prefix objects, and drops redundant per-element
    # `name:` keys — which is what LinkML tooling and humans expect.
    doc = schema_as_dict(schema)

    # Canonical order, so the released schema is byte-stable across builds and a
    # diff between two releases carries only real change. Without this, prefixes
    # follow set-iteration order (which Python randomizes per process via
    # PYTHONHASHSEED) and class slot lists follow DuckDB column order, so two
    # semantically identical builds serialize differently — see issue #253.
    # Ordering the emitted mapping is what makes the output independent of both.
    for key in ("prefixes", "slots", "classes"):
        if isinstance(doc.get(key), dict):
            doc[key] = {name: doc[key][name] for name in sorted(doc[key])}
    for class_def in doc.get("classes", {}).values():
        if class_def.get("slots"):
            class_def["slots"] = _canonical_slot_order(class_def["slots"])
        if isinstance(class_def.get("attributes"), dict):
            attrs = class_def["attributes"]
            class_def["attributes"] = {name: attrs[name] for name in sorted(attrs)}

    return yaml.dump(doc, sort_keys=False, allow_unicode=True)


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


# Biolink ranges that map to non-string DuckDB scalar types. Anything not
# listed here defaults to VARCHAR (covers string, uriorcurie, label_type,
# narrative_text, all enums, all class CURIE references, etc.).
_RANGE_TO_DUCKDB_SCALAR: dict[str, str] = {
    "integer": "BIGINT",
    "float": "DOUBLE",
    "double": "DOUBLE",
    "boolean": "BOOLEAN",
}

# Inverse of the above for recovering a LinkML range from a computed, non-Biolink
# DuckDB column (e.g. `has_phenotype_count` BIGINT). Lossy — DUCKDB DOUBLE can't
# distinguish float from double — so this only fills slots Biolink didn't already
# range at derive time, where the precise range is unknown anyway.
_DUCKDB_SCALAR_TO_RANGE: dict[str, str] = {
    "BIGINT": "integer",
    "INTEGER": "integer",
    "DOUBLE": "float",
    "FLOAT": "float",
    "BOOLEAN": "boolean",
}

# Biolink ranges treated as "primitive" for the purpose of multivalued
# dispatch: their multivalued form is a list of scalars in JSONL, never a
# list of struct objects. Class-typed multivalued slots are dispatched via
# the inlined / inlined_as_list LinkML flags instead.
_PRIMITIVE_RANGE_NAMES: frozenset[str] = frozenset(
    {
        "string",
        "uriorcurie",
        "iri type",
        "iriortext",
        "label type",
        "narrative text",
        "symbol type",
        "chemical formula value",
        "biological sequence",
        "date",
        "datetime",
        "time",
    }
)


def _scalar_for_range(rng: str) -> str:
    return _RANGE_TO_DUCKDB_SCALAR.get(rng, "VARCHAR")


def _duckdb_type_for_class(sv: SchemaView, class_name: str, depth: int = 0, max_depth: int = 2) -> str:
    """Build a DuckDB STRUCT(...) type for a Biolink class's induced slots.

    Recursive for nested class-typed slots that are `inlined_as_list`, bounded
    by `max_depth`. Returns `JSON` when depth is exceeded or the class is
    unknown — a safe fallback that preserves the literal value.
    """
    if depth > max_depth:
        return "JSON"
    try:
        slots = sv.class_induced_slots(class_name)
    except Exception:
        return "JSON"
    fields: list[tuple[str, str]] = []
    for s in slots:
        col = _snake_case(s.name)
        rng = str(s.range) if s.range else "string"
        if rng in _PRIMITIVE_RANGE_NAMES or rng in _RANGE_TO_DUCKDB_SCALAR:
            scalar = _scalar_for_range(rng)
            inner = f"{scalar}[]" if s.multivalued else scalar
        elif s.multivalued and s.inlined_as_list:
            inner = f"{_duckdb_type_for_class(sv, rng, depth + 1, max_depth)}[]"
        elif s.multivalued and s.inlined:
            struct = _duckdb_type_for_class(sv, rng, depth + 1, max_depth)
            inner = f"MAP(VARCHAR, {struct})" if struct != "JSON" else "JSON"
        elif s.multivalued:
            inner = "VARCHAR[]"  # list of CURIE references
        else:
            inner = "VARCHAR"  # scalar CURIE reference
        fields.append((col, inner))
    fields_sql = ", ".join(f'"{n}" {t}' for n, t in fields)
    return f"STRUCT({fields_sql})"


def duckdb_columns_for_slots(
    slots: list[str],
    root_class: str,
    biolink_schemaview: SchemaView,
    declared_outputs: dict[str, dict] | None = None,
    strict: bool = True,
) -> dict[str, str]:
    """Map a list of slot names to DuckDB column types, dispatched on Biolink.

    Returned dict is suitable for DuckDB's `read_json(..., columns={...})`
    parameter — bypasses schema inference entirely for JSONL files where we
    already know the slot set.

    Type dispatch follows LinkML semantics:

    | LinkML flags                                | DuckDB type             |
    |---------------------------------------------|-------------------------|
    | primitive range, scalar                     | `<scalar>` (VARCHAR/…)  |
    | primitive range, multivalued                | `<scalar>[]`            |
    | class range, scalar                         | `VARCHAR` (CURIE ref)   |
    | class range, multivalued + inlined_as_list  | `STRUCT(...)[]`         |
    | class range, multivalued + inlined          | `MAP(VARCHAR, STRUCT)`  |
    | class range, multivalued, neither flag      | `VARCHAR[]` (refs)      |

    `root_class` is the Biolink class to use as context for `induced_slot`
    lookups — `ENTITY_ROOT` for node files, `ASSOCIATION_ROOT` for edge files.

    With `strict=True` (default), slots that match no Biolink slot, no koza
    extra, and no declared output raise `UnknownSlotsError` — the ADR-0001
    contract applied to JSONL input. With `strict=False`, unknown slots map
    to `VARCHAR` so the loader can still read whatever's in the file.
    """
    declared_outputs = declared_outputs or {}
    pool = _biolink_slot_pool(biolink_schemaview, root_class)

    columns: dict[str, str] = {}
    rejected: list[str] = []
    for slot in slots:
        if slot in declared_outputs:
            spec = declared_outputs[slot]
            rng = spec.get("range", "string")
            mv = bool(spec.get("multivalued"))
            scalar = _scalar_for_range(rng)
            columns[slot] = f"{scalar}[]" if mv else scalar
            continue
        if slot in KOZA_INGEST_EXTRAS:
            spec = KOZA_INGEST_EXTRAS[slot]
            columns[slot] = _scalar_for_range(spec.get("range", "string"))
            continue
        if slot not in pool:
            rejected.append(slot)
            continue
        try:
            s = biolink_schemaview.induced_slot(slot.replace("_", " "), root_class)
        except Exception:
            columns[slot] = "VARCHAR"
            continue
        rng = str(s.range) if s.range else "string"
        if rng in _PRIMITIVE_RANGE_NAMES or rng in _RANGE_TO_DUCKDB_SCALAR:
            scalar = _scalar_for_range(rng)
            columns[slot] = f"{scalar}[]" if s.multivalued else scalar
        elif not s.multivalued:
            columns[slot] = "VARCHAR"  # scalar CURIE reference to a class instance
        elif s.inlined_as_list:
            columns[slot] = f"{_duckdb_type_for_class(biolink_schemaview, rng)}[]"
        elif s.inlined:
            struct = _duckdb_type_for_class(biolink_schemaview, rng)
            columns[slot] = f"MAP(VARCHAR, {struct})" if struct != "JSON" else "JSON"
        else:
            columns[slot] = "VARCHAR[]"  # multivalued CURIE references

    if rejected:
        if strict:
            details = ", ".join(rejected)
            raise UnknownSlotsError(
                f"{len(rejected)} slot(s) match no Biolink slot, koza extra, or "
                f"declared output for root class {root_class!r}: {details}"
            )
        for slot in rejected:
            columns[slot] = "VARCHAR"

    return columns


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


# --- schema overlay (issue #262) ---------------------------------------------

# The graph classes an overlay may refine via `slot_usage`. They are the
# column-bearing classes: `Entity` ↔ `nodes`, `Association` ↔ `edges`.
_GRAPH_CLASSES = frozenset(_TABLE_TO_CLASS.values())

# Top-level keys of a LinkML schema an overlay may carry. Only `classes` and
# `slots` are applied; the rest are accepted so an overlay can be a complete,
# independently valid LinkML document.
_OVERLAY_APPLIED_KEYS = frozenset({"classes", "slots"})
_OVERLAY_IGNORED_KEYS = frozenset(
    {"id", "name", "title", "description", "version", "license", "prefixes",
     "default_prefix", "default_range", "imports"}
)


# Classes closurize builds from the denormalized views; an overlay can't define
# them (closurize would discard it). Refine `Entity` / `Association` instead.
_RESERVED_OVERLAY_CLASSES = frozenset({"DenormalizedEntity", "DenormalizedAssociation"})

# Boolean-expression slots whose members carry their own `range`.
_RANGE_EXPRESSIONS = ("any_of", "exactly_one_of", "none_of", "all_of")


def load_schema_overlay(path) -> dict:
    """Read a schema overlay YAML and check everything that doesn't need the
    graph (see `check_schema_overlay`), so a missing or malformed overlay fails
    before a join loads any files."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Schema overlay not found: {path}")
    with open(path) as f:
        overlay = yaml.safe_load(f) or {}
    if not isinstance(overlay, dict):
        raise ValueError(f"Schema overlay {path} must be a YAML mapping")
    check_schema_overlay(overlay)
    return overlay


def check_schema_overlay(overlay: dict) -> SchemaDefinition:
    """Graph-independent checks of an overlay; returns it parsed.

    Rejects unsupported top-level keys, LinkML fields the metamodel doesn't
    know (misspellings), anything but `slot_usage` on `Entity` /
    `Association`, and the closurize-owned `Denormalized*` class names.
    """
    unknown = set(overlay) - _OVERLAY_APPLIED_KEYS - _OVERLAY_IGNORED_KEYS
    if unknown:
        raise ValueError(f"Schema overlay has unsupported keys: {sorted(unknown)}")
    raw_classes = overlay.get("classes") or {}
    reserved = sorted(set(raw_classes) & _RESERVED_OVERLAY_CLASSES)
    if reserved:
        raise ValueError(
            f"Schema overlay may not define {reserved}: closurize builds those classes; "
            f"refine Entity / Association instead"
        )
    for class_name in sorted(set(raw_classes) & _GRAPH_CLASSES):
        extra = set(raw_classes[class_name] or {}) - {"slot_usage"}
        if extra:
            raise ValueError(
                f"Schema overlay may only set slot_usage on {class_name}, got {sorted(extra)}"
            )
    # Parse through the LinkML metamodel so misspelled slot/class fields fail here.
    return SchemaDefinition(
        id="overlay",
        name="overlay",
        classes=raw_classes,
        slots=overlay.get("slots") or {},
    )


def _slot_ranges(slot: SlotDefinition) -> set[str]:
    """`range` of a slot definition plus those inside any_of / exactly_one_of / ..."""
    ranges = {str(slot.range)} if slot.range else set()
    for expression in _RANGE_EXPRESSIONS:
        for member in getattr(slot, expression) or []:
            if member.range:
                ranges.add(str(member.range))
    return ranges


def _column_shape(col_type: str | None) -> tuple[bool, bool] | None:
    """`(is_list, holds_records)` for a DuckDB column type, or None if unknown."""
    parsed = _parse_duckdb_type(col_type)
    if parsed is None:
        return None
    element, is_list = _list_element(parsed)
    return is_list, element.id in ("struct", "map")


def _check_against_columns(
    label: str, slot: SlotDefinition, shapes: list[tuple[bool, bool]]
) -> None:
    """Reject a slot_usage / override whose shape contradicts the data it describes."""
    for is_list, holds_records in shapes:
        if slot.multivalued is not None and bool(slot.multivalued) != is_list:
            raise ValueError(
                f"Schema overlay sets {label} multivalued: {bool(slot.multivalued)}, but "
                f"its column is {'a list' if is_list else 'single-valued'}"
            )
        if (slot.inlined or slot.inlined_as_list) and not holds_records:
            raise ValueError(
                f"Schema overlay declares {label} inlined, but its column doesn't hold "
                f"records (STRUCT / MAP); inlined records need a record column"
            )
        if slot.inlined is False and holds_records:
            raise ValueError(
                f"Schema overlay declares {label} not inlined, but its column holds records"
            )


def apply_schema_overlay(
    schema: SchemaDefinition,
    overlay: dict,
    sv: SchemaView,
    column_types: dict[str, dict[str, str]] | None = None,
) -> None:
    """Apply a LinkML schema fragment to a derived graph schema, in place.

    - `classes.Entity.slot_usage` / `classes.Association.slot_usage`: refine
      how a column's slot is shaped for that class — the LinkML-native way to
      narrow a slot. Kept as `slot_usage` on the class, so
      `SchemaView.induced_slot` honors it and closurize carries it onto the
      denormalized classes.
    - any other `classes` entry: added to the schema as written (replacing a
      derived class of that name, with a warning).
    - top-level `slots`: replace the named fields of a derived slot
      definition. For changes that aren't refinements; each is logged.

    `column_types` (`{"Entity": {column: duckdb type}, "Association": {...}}`)
    lets slot_usage and overrides be checked against the data: `inlined` needs
    a record column, and `multivalued` must match whether the column is a list.

    Every class reference must resolve: `range` (also inside `any_of` and
    friends), `is_a` and `mixins` name a class from the overlay, the schema, or
    Biolink (which gets a standalone, primitive-reduced definition so the
    export stays loadable with only `linkml:types`); `slots` lists name slots
    in the graph. The result must load in a SchemaView.
    """
    parsed = check_schema_overlay(overlay)
    raw_slots = overlay.get("slots") or {}
    column_types = column_types or {}
    referenced_classes: set[str] = set()

    def shapes_for(slot_name: str, classes) -> list[tuple[bool, bool]]:
        shapes = []
        for class_name in classes:
            shape = _column_shape(column_types.get(class_name, {}).get(slot_name))
            if shape is not None:
                shapes.append(shape)
        return shapes

    for class_name, class_def in parsed.classes.items():
        if class_name in _GRAPH_CLASSES:
            target = schema.classes[class_name]
            for slot_name, usage in (class_def.slot_usage or {}).items():
                if slot_name not in target.slots:
                    raise ValueError(
                        f"Schema overlay slot_usage names {slot_name!r}, which is not "
                        f"a slot of {class_name} in this graph"
                    )
                _check_against_columns(
                    f"{class_name}.{slot_name}", usage, shapes_for(slot_name, [class_name])
                )
                target.slot_usage[slot_name] = usage
                referenced_classes |= _slot_ranges(usage)
            continue
        if class_name in schema.classes:
            logger.warning(f"Schema overlay replaces derived class {class_name!r}")
        schema.classes[class_name] = class_def
        for parent in [class_def.is_a, *(class_def.mixins or [])]:
            if parent:
                referenced_classes.add(str(parent))
        for slot_name in class_def.slots or []:
            if slot_name not in schema.slots and slot_name not in parsed.slots:
                raise ValueError(
                    f"Schema overlay class {class_name!r} lists slot {slot_name!r}, "
                    f"which is not in this graph or the overlay"
                )
        for attr in (class_def.attributes or {}).values():
            referenced_classes |= _slot_ranges(attr)
        for usage in (class_def.slot_usage or {}).values():
            referenced_classes |= _slot_ranges(usage)

    for slot_name, slot_def in parsed.slots.items():
        # `schema.slots` may be a JsonObj (no `.get`) on a freshly derived schema.
        derived = schema.slots[slot_name] if slot_name in schema.slots else None
        if derived is None:
            raise ValueError(
                f"Schema overlay overrides slot {slot_name!r}, which is not in this graph"
            )
        fields = set(raw_slots[slot_name] or {})
        _check_against_columns(slot_name, slot_def, shapes_for(slot_name, _GRAPH_CLASSES))
        for field in fields:
            setattr(derived, field, getattr(slot_def, field))
        # A non-class range can't be inlined; don't leave inferred flags behind.
        if "range" in fields and str(slot_def.range) in _LINKML_BUILTIN_PRIMITIVES:
            for flag in ("inlined", "inlined_as_list"):
                if flag not in fields:
                    setattr(derived, flag, None)
        logger.info(f"Schema overlay overrides slot {slot_name!r}: {sorted(fields)}")
        referenced_classes |= _slot_ranges(slot_def)

    biolink_classes = {camelcase(name): name for name in sv.all_classes()}
    for name in sorted(referenced_classes):
        if name in schema.classes or name in _LINKML_BUILTIN_PRIMITIVES:
            continue
        biolink_class = biolink_classes.get(name)
        if biolink_class is None:
            raise ValueError(
                f"Schema overlay references {name!r}, which is neither defined "
                f"in the overlay, a LinkML built-in type, nor a Biolink class"
            )
        schema.classes[name] = _standalone_biolink_class(sv, biolink_class)

    _check_schema_resolves(schema)


def _check_schema_resolves(schema: SchemaDefinition) -> None:
    """Fail at seed time, not at export or in a consumer, if the overlaid schema
    doesn't load: every class's induced slots must resolve in a SchemaView."""
    # Round-trip as koza stores it: normalizes JsonObj containers a freshly
    # derived schema holds, and leaves `schema` itself untouched.
    candidate = yaml_loader.loads(yaml_dumper.dumps(schema), target_class=SchemaDefinition)
    if "linkml:types" not in (candidate.imports or []):
        candidate.imports = list(candidate.imports or []) + ["linkml:types"]
    candidate.default_range = candidate.default_range or "string"
    try:
        view = SchemaView(candidate)
        for class_name in view.all_classes():
            view.class_induced_slots(class_name)
    except Exception as e:
        raise ValueError(f"Schema overlay leaves the graph schema unresolvable: {e}") from e


def _standalone_biolink_class(sv: SchemaView, biolink_class: str) -> ClassDefinition:
    """A Biolink class's induced slots as self-contained `attributes`, ranges
    reduced to LinkML primitives (class-valued attributes become CURIE refs)."""
    attributes: dict[str, SlotDefinition] = {}
    for slot in sv.class_induced_slots(biolink_class):
        name = _snake_case(slot.name)
        attributes[name] = SlotDefinition(
            name=name,
            range=_primitive_range(sv, slot.range),
            multivalued=slot.multivalued or None,
            exact_mappings=[f"biolink:{name}"],
        )
    return ClassDefinition(
        name=camelcase(biolink_class),
        class_uri=sv.get_uri(sv.get_class(biolink_class)),
        attributes=attributes,
    )
