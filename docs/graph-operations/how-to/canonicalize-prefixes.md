# Canonicalize Prefixes

Two graphs that spell the same CURIE prefix differently (`hgnc:746` vs
`HGNC:746`) join and append without error — and land as disjoint node sets.
The prefix report makes that visible before it happens; `koza canonicalize`
repairs it.

Both operations classify every prefix appearing in `nodes.id`,
`edges.subject`, and `edges.object` against a
[prefixmaps](https://github.com/linkml/prefixmaps) context (default:
`merged`):

- **canonical** — exact match in the context
- **case_variant** — matches a context prefix case-insensitively but not
  exactly (`hgnc` → `HGNC`)
- **unknown** — not in the context at all (internal prefixes, typos)

## Audit a graph's prefixes

```bash
koza report prefixes -d graph.duckdb -o prefixes.yaml
```

Console output flags the actionable cases:

```
Prefixes in graph: 12 (10 canonical, 1 case variants, 1 unknown to context 'merged')
  ⚠️  hgnc → HGNC (15,297 references)
```

The YAML report lists every prefix with per-column counts, so a mixed graph
shows `HGNC` and `hgnc` side by side before anyone joins against it.

## Repair case-variant prefixes

```bash
# Preview what would change
koza canonicalize graph.duckdb --dry-run

# Apply
koza canonicalize graph.duckdb

# Use a different prefixmaps context
koza canonicalize graph.duckdb --context bioregistry.upper
```

Canonicalize rewrites node ids and edge subject/object references whose
prefix is a case variant of a canonical prefix. Original identifiers are
preserved in `original_id` (nodes) and `original_subject` /
`original_object` (edges) — the same columns `koza normalize` uses, and
existing values there are never overwritten.

## What canonicalize deliberately does not do

- **It never renames one known prefix to a different one.** Mapping
  `NCBIGene` to `ENTREZ` is an identifier-level decision — that is
  [`koza normalize`](normalize-ids.md) with SSSOM mappings.
- **It never touches unknown prefixes.** A prefix absent from the context is
  reported for a person to look at; it may be an internal namespace or a
  typo, and no registry can tell those apart.
- **It does not deduplicate.** A repaired id can land on an id the graph
  already has (`hgnc:746` arriving at an existing `HGNC:746` row). Collisions
  are counted and warned about; fold them with the dedup machinery
  (see [Clean Graphs](clean-graph.md)).

## Typical workflow

```bash
# Before appending an external graph onto a reference graph:
koza report prefixes -d external.duckdb        # audit
koza canonicalize external.duckdb              # repair case variants
koza append reference.duckdb -n external_nodes.jsonl -e external_edges.jsonl
```
