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

# Repair only the prefix you care about (repeatable)
koza canonicalize graph.duckdb --only hgnc

# Use a different prefixmaps context
koza canonicalize graph.duckdb --context bioregistry.upper
```

Check the dry run before applying. A context's canonical spelling is not
always the one your graph has settled on: against `merged`, for example,
`FBDV` becomes `FBdv`, `Orphanet` becomes `ORPHANET` and `OBO` becomes `obo`.
When only some of the reported variants are real problems, repair just those
with `--only`.

Canonicalize rewrites node ids and edge subject/object references whose
prefix is a case variant of a canonical prefix. Original identifiers are
preserved in `original_id` (nodes) and `original_subject` /
`original_object` (edges) — the same columns `koza normalize` uses, and
existing values there are never overwritten. All rewrites run in one
transaction: if anything fails, the database is left unchanged.

Only the `nodes` and `edges` tables are rewritten, and within them only
`id`, `subject` and `object`. Derived tables (`closure`, `denormalized_*`,
`mappings`, `information_content`, ...) and other CURIE-valued columns
(`in_taxon`, `xref`, qualifiers, ...) keep the old spellings. Canonicalize
warns when other tables exist; run it before building derived tables, or
rebuild them afterwards.

## What canonicalize deliberately does not do

- **It never renames one known prefix to a different one.** Mapping
  `NCBIGene` to `ENTREZ` is an identifier-level decision — that is
  [`koza normalize`](normalize-ids.md) with SSSOM mappings.
- **It never touches unknown prefixes.** A prefix absent from the context is
  reported for a person to look at; it may be an internal namespace or a
  typo, and no registry can tell those apart.
- **It does not deduplicate.** A repaired id can land on an id the graph
  already has (`hgnc:746` arriving at an existing `HGNC:746` row), and two
  edges can end up with the same subject/predicate/object. Both kinds of
  collision are counted and warned about on every run, but the rows are kept
  as they are. There is no standalone dedup command; note that id-based
  deduplication (in `koza merge` / `koza append --deduplicate`) keeps the
  first row per id rather than merging rows, and does not catch edges whose
  ids differ.

## Typical workflow

```bash
# Before appending an external graph onto a reference graph:
koza report prefixes -d external.duckdb        # audit
koza canonicalize external.duckdb              # repair case variants
koza export external.duckdb -o external/ -f jsonl
koza append reference.duckdb --input-dir external/
```
