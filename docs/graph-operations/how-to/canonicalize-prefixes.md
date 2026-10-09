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

# Apply and remove the duplicate rows the repair creates
koza canonicalize graph.duckdb --deduplicate

# Use a different prefixmaps context
koza canonicalize graph.duckdb --context bioregistry.upper
```

Check the dry run before applying. A context's canonical spelling is not
always the one your graph has settled on: against `merged`, for example,
`FBDV` becomes `FBdv`, `Orphanet` becomes `ORPHANET` and `OBO` becomes `obo`.
When only some of the reported prefixes are real problems, repair just those
with `--only`.

Canonicalize rewrites node ids and edge subject/object references whose
prefix is an alternately-cased spelling of a canonical prefix. It does not
write `original_id` / `original_subject` / `original_object`; those columns
belong to [`koza normalize`](normalize-ids.md). Instead, every change is
recorded in the `prefix_canonicalization_log` table (see below). The
rewrites, the audit rows and any deduplication run in one transaction: if
anything fails, the database is left unchanged.

Only the `nodes` and `edges` tables are rewritten, and within them only
`id`, `subject` and `object`. Derived tables (`closure`, `denormalized_*`,
`mappings`, `information_content`, ...) and other CURIE-valued columns
(`in_taxon`, `xref`, qualifiers, ...) keep the old spellings. Canonicalize
warns when other tables exist; rebuild them afterwards if you could not run
canonicalize first.

## Collisions and `--deduplicate`

A repaired id can land on an id the graph already has (`hgnc:746` arriving
at an existing `HGNC:746` row), and two edges can end up with the same
subject/predicate/object. Both kinds of collision are counted and warned
about. Without `--deduplicate` the rows are kept as they are.

With `--deduplicate`, canonicalize removes the extra rows in each colliding
group, in the same transaction as the rewrite. It keeps the row that was not
rewritten (the pre-existing canonical row) when there is one, then the first
by `file_source`, then the earliest inserted. Rows are removed, not merged:
properties on the dropped row are not copied onto the kept one.

Only groups that involve a rewritten row are touched. On a re-run that finds
nothing left to rewrite, canonicalize instead looks at ids in the prefixes
an earlier run canonicalized (according to the audit table), so collisions
left by an earlier run are still reported and `--deduplicate` can still
remove them. Within those prefixes this also catches duplicates that
predate canonicalization.

## The audit table

Each run that changes something appends rows to
`prefix_canonicalization_log`; earlier rows are never modified, so the
table is a history of runs. A run that finds nothing to rewrite or
deduplicate (including a plain re-run) adds nothing, and `--dry-run` never
writes.

| Column | Meaning |
|--------|---------|
| `run_at` | UTC timestamp, shared by every row one run writes |
| `context` | prefixmaps context the run used |
| `action` | `rewrite` or `deduplicate` |
| `table_name` | `nodes` or `edges` |
| `column_name` | `rewrite`: the column rewritten (`id`, `subject`, `object`). `deduplicate`: the collision key (`id` or `subject,predicate,object`) |
| `old_prefix` / `new_prefix` | spelling before and after (`rewrite` only) |
| `example_value` | one affected value: an id before the rewrite, or the key of a group that lost rows |
| `row_count` | rows rewritten, or rows removed |

There is one `rewrite` row per table, column and prefix, and one
`deduplicate` row per table.

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
