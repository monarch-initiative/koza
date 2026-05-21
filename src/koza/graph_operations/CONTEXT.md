# Graph Operations Context

Terminology for koza's graph operations package, which wraps DuckDB to perform KGX-format graph transforms (join, deduplicate, normalize, prune, split, append, merge, report) behind a Python CLI.

## Language

**Graph schema**:
A LinkML schema stored as metadata inside each koza-built DuckDB, describing the slots and tables for that graph. Seeded at graph creation by flattening Biolink's entity and association hierarchies into two classes (`Entity` and `Association`) and intersecting with input file headers. Evolved by operations as they run. Exportable as `derived-schema.yaml` on demand. Aligns with monarch-app's `Entity`/`Association` naming convention (post-closurizer).
_Avoid_: derived schema, run schema, ingest contract, flat KGX schema, Node/Edge (those refer to the DuckDB tables).

**Entity** / **Association**:
The two flat classes in the graph schema for the ingest stage, corresponding to the `nodes` and `edges` tables respectively. Slot names are snake_case throughout (e.g. `original_subject`, `provided_by`).
_Avoid_: Node, Edge (those name the DuckDB tables, not the graph schema classes).

**DenormalizedEntity** / **DenormalizedAssociation**:
The post-closurize counterparts, corresponding to the `denormalized_nodes` and `denormalized_edges` tables. `is_a` Entity / Association respectively, adding closurizer-produced slots (`{field}_label`, `{field}_category`, `{field}_namespace`, `{field}_closure`, `{field}_closure_label`, per-predicate aggregations on nodes). Added to the stored schema by the **Closurize** operation. Note: monarch-app currently uses `Entity`/`Association` for what we call `DenormalizedEntity`/`DenormalizedAssociation` — alignment is a downstream decision.
_Avoid_: ClosurizedEntity, ExpandedEntity.

**Schema seeding**:
The process that runs at graph creation: read input headers, intersect with Biolink slots, union with koza extras (ingest provenance + every operation's declared outputs), write the derived schema and a full copy of the Biolink YAML into DuckDB metadata, and emit `CREATE TABLE` statements for `nodes` and `edges`. The only time koza reads Biolink from the python environment.
_Avoid_: schema build (covers two distinct moments now — be specific), schema derivation, schema generation.

**Schema evolution**:
The process that runs when an operation produces new slots: operation declares output slots via its `DECLARED_OUTPUTS`, the schema module `ALTER TABLE`s the relevant DuckDB tables and updates the stored schema metadata in the same transaction. On unseeded databases (graphs from before the schema feature existed), `ensure_slots` gracefully degrades to a plain `ALTER TABLE` so operations remain usable — see ADR-0002.
_Avoid_: schema migration, schema mutation.

**Schema rebase**:
An explicit `koza schema rebase` operation that pulls a fresh Biolink from the python environment, replaces the stored copy in the DuckDB, and surfaces deprecations, renames, and newly-admissible slots from existing data. The only way Biolink updates land in an existing graph.
_Avoid_: schema upgrade, schema sync.

**Slot**:
A LinkML term for a column / property. Used in place of "column," "field," or "property" when discussing the typed surface.
_Avoid_: column (when referring to the contract — fine when referring to raw DuckDB tables), field, property.

**Slot registry**:
A small generated Python module of string constants emitted from the graph schema, used to construct SQL with names that fail at import time on typos. Independent of pydantic-gen.
_Avoid_: column constants, field names module.

**Koza extras**:
Slots koza injects that are not in Biolink — ingest provenance (`file_source`, `provided_by`) and operation outputs (`original_subject`, `mapping_source`, etc.). Part of the graph schema.
_Avoid_: koza columns, custom fields.

**Declared outputs**:
A module-level constant (`DECLARED_OUTPUTS`) on each operation module that lists the slots the operation produces. The schema module imports these at startup from a hardcoded operation-module list and unions them into the koza extras at schema seeding. Lets the strict-reject set know about slots even before any operation that produces them has run.
_Avoid_: produced slots, output schema, operation contract.

**Operation**:
One of the high-level graph transforms exposed by the CLI: join, deduplicate, normalize, prune, split, append, merge, closurize, report. Each is a module under `koza/graph_operations/`.
_Avoid_: command, action, transform (transform refers to the koza ingest side).

**Closurize**:
The operation that applies a relation-graph closure to a merged graph database. Produces `denormalized_nodes` and `denormalized_edges` as VIEWs over base tables (~50% smaller DuckDB than the historical materialized shape), plus per-predicate node-extension side tables and the materialized `closure_id` / `closure_label` / `descendants_id` / `descendants_label` tables. Evolves the stored schema to include `DenormalizedEntity` / `DenormalizedAssociation` classes whose slot lists come from the actual produced views. Migrated from the `closurizer` package in May 2026; this module is now its canonical home, the standalone package is no longer maintained.
_Avoid_: denormalize (too generic), expand.

**Graph database**:
The `GraphDatabase` class wrapping a DuckDB connection. Owns the data tables (`nodes`, `edges`, `singleton_nodes`, `dangling_edges`, etc.) and the schema metadata table (`_koza_schema`) holding the derived schema and the seeded Biolink YAML.
_Avoid_: db, connection, store.

## Relationships

- A **Graph schema** is stored inside one **Graph database** and describes its contents at the current moment.
- A **Graph schema** contains one class per DuckDB table currently in the pipeline state: at minimum **Entity** (`nodes`) and **Association** (`edges`); when closurizer is in play, also **DenormalizedEntity** (`denormalized_nodes`) and **DenormalizedAssociation** (`denormalized_edges`).
- Each class is composed of **Slots** drawn from Biolink (subsetted) plus **Koza extras**.
- An **Operation** consumes **Slots** and may produce them via its **Declared outputs**; **Schema evolution** runs when an operation's declared outputs aren't yet materialized in the database.
- A **Slot registry** is generated from the **Graph schema** and used by operations to construct SQL.
- A **Schema rebase** is the only path by which the Biolink copy inside a **Graph database** changes after **Schema seeding**.

## Example dialogue

> **Dev:** "When `normalize` writes `original_subject`, does that column need to exist in Biolink?"
> **Domain expert:** "No — it's a **Koza extra** on the **Association** class. Normalize lists it in its **Declared outputs**, so the schema module includes it in the strict-reject set from **Schema seeding** onward, even before normalize runs. When normalize does run, **Schema evolution** materializes the column."

> **Dev:** "What happens if an input file has a column that isn't a Biolink slot and isn't a koza extra?"
> **Domain expert:** "Strict reject. The valid slot set is `(Biolink ∪ koza extras ∪ every operation's declared outputs)` — anything outside that fails at load with a clear error."

> **Dev:** "Biolink released 4.5. How does my existing graph get the new slots?"
> **Domain expert:** "Run **Schema rebase**. Routine operations never re-read Biolink from the environment — the copy stored at **Schema seeding** is authoritative until you explicitly rebase."
