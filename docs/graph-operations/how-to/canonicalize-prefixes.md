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
- **alternate_casing** — matches a context prefix case-insensitively but
  not exactly (`hgnc` → `HGNC`)
- **unknown** — not in the context at all (internal prefixes, typos)

## Audit a graph's prefixes

```bash
koza report prefixes -d graph.duckdb -o prefixes.yaml
```

Console output flags the actionable cases:

```
Prefixes in graph: 12 (10 canonical, 1 with alternate casing, 1 unknown to context 'merged')
  ⚠️  hgnc → HGNC (15,297 references)
```

The YAML report lists every prefix with per-column counts, so a mixed graph
shows `HGNC` and `hgnc` side by side before anyone joins against it.

## Repair prefixes with alternate casing

Run canonicalize **before** `koza closurize` / denormalization and before
computing information content: only `nodes` and `edges` are rewritten, so
anything derived from them beforehand keeps the old ids.

```bash
# Preview what would change
koza canonicalize graph.duckdb --dry-run

# Apply
koza canonicalize graph.duckdb

# Repair only the prefix you care about (repeatable)
koza canonicalize graph.duckdb --only hgnc

# Apply and remove the duplicate rows the repair creates (preview first)
koza canonicalize graph.duckdb --dry-run --deduplicate
koza canonicalize graph.duckdb --deduplicate

# Use a different prefixmaps context
koza canonicalize graph.duckdb --context bioregistry.upper
```

Check the dry run before applying. A context's canonical spelling is not
always the one your graph has settled on: against `merged`, for example,
`FBDV` becomes `FBdv`, `Orphanet` becomes `ORPHANET` and `OBO` becomes `obo`.
When only some of the reported prefixes are real problems, repair just those
with `--only`. An `--only` prefix that appears nowhere in the graph is an
error (with close matches suggested), so a typo can't silently do nothing.

Canonicalize rewrites node ids and edge subject/object references whose
prefix is an alternately-cased spelling of a canonical prefix. It does not
write `original_id` / `original_subject` / `original_object`; those columns
belong to [`koza normalize`](normalize-ids.md). Instead, every change is
recorded in the `prefix_canonicalization_log` table (see below). The
rewrites, the audit rows and any deduplication run in one transaction: if
anything fails, the database is left unchanged. `--dry-run` runs the same
transaction and rolls it back.

Only the `nodes` and `edges` tables are rewritten, and within them only
`id`, `subject` and `object`. Derived tables (`closure`, `denormalized_*`,
`mappings`, `information_content`, ...) and other CURIE-valued columns
(`in_taxon`, `xref`, qualifiers, ...) keep the old spellings. Canonicalize
warns when other tables exist; rebuild them afterwards if you could not run
canonicalize first.

## Node collisions and `--deduplicate`

A rewritten node id can land on an id the graph already has (`hgnc:746`
arriving at an existing `HGNC:746` row). Collisions are judged only against
node rows rewritten **in the same run**: a rewritten node collides when
another row has the same `id`. Duplicate ids that existed before the run
(two `HGNC:1` rows) are never counted and never touched.

`--deduplicate` applies to **nodes only**. Edges are never deduplicated:
rewritten edge subjects and objects are left as they are, even if an edge
ends up looking like another one.

Without `--deduplicate`, node collisions are counted and warned about, and
the rows are kept. With `--deduplicate`, the rewritten row is removed and
the pre-existing row is kept; if only rewritten rows collide with each other
(say `hgnc:1` and `Hgnc:1`), one is kept, the first by `file_source` and
then the earliest inserted. Rows are removed, not merged: a removed node
may carry a different `name` or other properties than the one kept.

`--deduplicate` must be passed **on the run that does the repair**. A later
run finds nothing to rewrite, so `--deduplicate` then removes nothing. To
see what a repair would do first, use `--dry-run --deduplicate`: the dry run
performs the whole operation and rolls it back, so its counts are exact.

Removed rows are never simply deleted. They are copied, in the same
transaction, into `prefix_canonicalization_removed_nodes`, which has the
same columns as `nodes` plus `run_at`:

```sql
SELECT * FROM prefix_canonicalization_removed_nodes ORDER BY run_at;
```

## The audit table

Each run that changes something appends rows to
`prefix_canonicalization_log`; earlier rows are never modified, so the
table is a history of runs. A run that finds nothing to rewrite adds
nothing, and `--dry-run` never writes. The log records what changed, not
enough to reverse it: rewritten values are not kept.

| Column | Meaning |
|--------|---------|
| `run_at` | UTC timestamp, shared by every row one run writes (and by the removed-nodes rows) |
| `context` | prefixmaps context the run used |
| `action` | `rewrite` or `deduplicate` |
| `table_name` | `nodes` or `edges` (`deduplicate` rows are always `nodes`) |
| `column_name` | `rewrite`: the column rewritten (`id`, `subject`, `object`). `deduplicate`: `id` |
| `old_prefix` / `new_prefix` | spelling before and after (`rewrite` only) |
| `example_value` | one affected value: an id before the rewrite, or the id of a removed node row |
| `row_count` | rows rewritten, or rows removed |

There is one `rewrite` row per table, column and prefix, and one
`deduplicate` row per run that removed nodes.

```sql
SELECT action, table_name, column_name, old_prefix, new_prefix, row_count
FROM prefix_canonicalization_log ORDER BY run_at;
```

## What canonicalize deliberately does not do

- **It never renames one known prefix to a different one.** Mapping
  `NCBIGene` to `ENTREZ` is an identifier-level decision — that is
  [`koza normalize`](normalize-ids.md) with SSSOM mappings.
- **It never touches unknown prefixes.** A prefix absent from the context is
  reported for a person to look at; it may be an internal namespace or a
  typo, and no registry can tell those apart.

## Typical workflow

```bash
# Before appending an external graph onto a reference graph:
koza report prefixes -d external.duckdb        # audit
koza canonicalize external.duckdb              # repair alternate casing
koza export external.duckdb -o external/ -f jsonl
koza append reference.duckdb --input-dir external/
```
