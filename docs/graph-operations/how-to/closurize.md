# Closurize a Graph

## Goal

Apply transitive closure expansion to a merged graph database so each edge carries the full ancestry of its subject and object — enabling hierarchy-aware search and faceting without recursive SQL.

After closurize, `denormalized_edges` and `denormalized_nodes` are queryable views: each edge row exposes `subject_closure`, `subject_closure_label`, `object_closure`, `object_closure_label`, and taxon/category/namespace labels for both endpoints. Each node row exposes per-predicate aggregations (e.g. `has_phenotype`, `has_phenotype_closure_label`) and descendants.

## Prerequisites

- A koza-built DuckDB containing `nodes` and `edges` tables (produced by `koza join` or `koza merge`).
- A relation-graph TSV: a three-column file `(subject_id, predicate_id, object_id)` enumerating one-hop relations from the ontology entailments you want closurized over. For Monarch, this is `phenio-relation-filtered.tsv` (the filtered output of phenio's ROBOT-based one-hop materialization).

## Basic Closurize

```bash
koza closurize graph.duckdb -c phenio-relation-filtered.tsv
```

This produces:

| Object | Kind | Purpose |
|---|---|---|
| `closure_id` | materialized table | per-node ancestor ID arrays |
| `closure_label` | materialized table | per-node ancestor label arrays |
| `descendants_id` / `descendants_label` | materialized tables | per-node descendant arrays |
| `node_<predicate>` | materialized table per `--node-field` | aggregated edge endpoints per node |
| `denormalized_edges` | **view** | edges joined to subject/object closure expansions |
| `denormalized_nodes` | **view** | nodes joined to side tables + descendants |

Plus two new columns added directly to `edges`: `evidence_count` (sum of evidence/publication array lengths) and `grouping_key` (a stable composite key over subject/predicate/object/negated).

## Configuring the Expansion

Two flavors of edge-field expansion:

- **Full closure expansion** (`--edge-field`): adds `_label`, `_category`, `_namespace`, `_closure`, `_closure_label`, and (for `subject`/`object`) `_taxon`/`_taxon_label`.
- **Label-only expansion** (`--edge-field-to-label`): adds `_label`, `_category`, `_namespace` — no closure arrays. Cheaper for fields where you don't need ancestry traversal.

Plus node-side per-predicate aggregations (`--node-field`): for each configured predicate, aggregates that predicate's objects per subject node into `<predicate>`, `<predicate>_label`, `<predicate>_count`, `<predicate>_closure`, `<predicate>_closure_label`.

### Monarch-style invocation

```bash
koza closurize graph.duckdb -c phenio-relation-filtered.tsv \
    --edge-field subject \
    --edge-field object \
    --edge-field disease_context_qualifier \
    --edge-field-to-label species_context_qualifier \
    --edge-field-to-label stage_qualifier \
    --edge-field-to-label sex_qualifier \
    --edge-field-to-label onset_qualifier \
    --edge-field-to-label frequency_qualifier \
    --node-field has_phenotype \
    --additional-node-constraints "e.negated IS NULL OR e.negated = false"
```

The `--additional-node-constraints` flag accepts a SQL `WHERE`-style fragment applied to the per-predicate edge join. Reference edges columns via the `e` alias.

## Schema Evolution

If the DuckDB was seeded (via [`koza join`](join-files.md)'s schema seam), closurize adds two new classes to the stored schema:

- `DenormalizedEntity is_a Entity` — with slots matching the actual columns of `denormalized_nodes`.
- `DenormalizedAssociation is_a Association` — with slots matching `denormalized_edges`.

Inspect via:

```bash
koza schema-export graph.duckdb -o graph-schema.yaml
```

The exported file is a standalone LinkML schema with `linkml:types` imported and `linkml`/`biolink` prefixes declared — directly consumable by `gen-pydantic`, `lsolr`, and other LinkML tooling. By default, `DenormalizedEntity` is renamed to `Entity` and `DenormalizedAssociation` to `Association` (consumer-facing names); pass `--raw` to preserve the internal naming.

## Memory Considerations

The closure aggregation involves `ARRAY_AGG`+`FLATTEN`+`LIST_DISTINCT` over per-node groups, which doesn't spill cleanly to disk. For a Monarch-scale graph (~1.5 M nodes, ~15 M edges), peak memory during closurize is ~25 GB. To cap:

```bash
DUCKDB_MEMORY_LIMIT=16GB koza closurize ...
```

Most chunks will still succeed; the closure aggregation chunk may OOM under tight caps. The graph schema seam is tolerant — if it doesn't get to the evolve step, downstream operations still work via the unseed fallback.

## Verification

Confirm the denormalized views are queryable:

```sql
-- All edges where the subject is a descendant of MONDO:0700096 (human disease)
SELECT subject_label, predicate, object_label
FROM denormalized_edges
WHERE list_contains(subject_closure, 'MONDO:0700096')
LIMIT 5;
```

And confirm `_koza_schema` knows about the new classes:

```bash
duckdb graph.duckdb "SELECT kind, length(content) FROM _koza_schema"
```

## Next Steps

- [`koza schema-export`](../reference/cli.md#koza-schema-export) — write the post-closurize schema as a release artifact.
- [Schema Handling](../explanation/schema-handling.md) — how the graph schema seam works.
