# How to Normalize IDs

## Goal

Apply SSSOM mappings to harmonize identifiers in edge references. This allows you to consolidate equivalent identifiers from different sources (e.g., mapping OMIM disease IDs to MONDO) so that edges reference consistent node identifiers.

## Prerequisites

- A DuckDB database with edges (created via `koza join`, `koza merge`, or `koza append`)
- One or more SSSOM mapping files that define the identifier mappings you want to apply

## Understanding SSSOM

[SSSOM (Simple Standard for Sharing Ontological Mappings)](https://mapping-commons.github.io/sssom/) is a standard format for representing mappings between ontology terms and other identifiers.

### SSSOM File Format

An SSSOM TSV file typically has an optional YAML header (lines starting with `#`) followed by tab-separated data:

```tsv
#curie_map:
#  MONDO: http://purl.obolibrary.org/obo/MONDO_
#  OMIM: https://omim.org/entry/
#  HP: http://purl.obolibrary.org/obo/HP_
#mapping_set_id: https://example.org/mappings/mondo-omim
subject_id	predicate_id	object_id	mapping_justification
MONDO:0005148	skos:exactMatch	OMIM:222100	semapv:ManualMappingCuration
MONDO:0007455	skos:exactMatch	OMIM:114500	semapv:ManualMappingCuration
MONDO:0008199	skos:exactMatch	OMIM:176000	semapv:ManualMappingCuration
```

### How Koza Uses SSSOM for Normalization

Koza uses a **simplifying assumption** when applying SSSOM mappings: it maps FROM the `object_id` TO the `subject_id`. This is a practical simplification for identifier normalization and does not reflect the full semantic meaning of SSSOM mapping files (where subject/object semantics depend on the predicate).

The relevant columns for normalization are:

- **subject_id**: The target identifier (what Koza normalizes TO)
- **object_id**: The source identifier (what Koza normalizes FROM)
- **predicate_id**: The mapping relationship (e.g., `skos:exactMatch`) - optionally used for filtering (see [Filtering by Mapping Predicate](#filtering-by-mapping-predicate)), never for determining direction
- **mapping_justification**: How the mapping was created (optional but recommended)

**Important**: Normalization changes **edge references** (the `subject` and `object` columns in the edges table), not the node IDs themselves. If an edge references an identifier that appears in the SSSOM `object_id` column, that reference is updated to the corresponding `subject_id`.

## Basic Normalization

Apply a single SSSOM file to normalize identifiers in your database.

### Step 1: Verify Your Database

First, check the current state of your edges:

```bash
# Count edges and check identifier patterns
duckdb graph.duckdb -c "
  SELECT COUNT(*) as edge_count FROM edges;
"

# See sample identifiers
duckdb graph.duckdb -c "
  SELECT DISTINCT subject FROM edges LIMIT 10;
"
```

### Step 2: Apply the Mapping

```bash
koza normalize graph.duckdb \
  --mappings mondo-omim.sssom.tsv
```

### Example Output

```
Loading SSSOM mappings...
  Loaded 45,678 unique mappings from 1 file(s)
Normalizing edge references...
  Normalized 12,345 edge subject/object references
Normalization completed successfully
```

## Multiple Mapping Files

When you have mappings from multiple sources, you can apply them all at once.

### Using Multiple Files

```bash
koza normalize graph.duckdb \
  -m mondo-omim.sssom.tsv \
  -m mondo-orphanet.sssom.tsv \
  -m hp-mp.sssom.tsv
```

### Using a Mappings Directory

If all your SSSOM files are in one directory:

```bash
koza normalize graph.duckdb \
  --mappings-dir ./mappings/
```

This loads all `.sssom.tsv` files from the specified directory.

### Order of Application

When using multiple mapping files:

1. Files are processed in the order specified (or alphabetically for `--mappings-dir`)
2. All mappings are loaded into a single mappings table before normalization
3. If the same `object_id` appears in multiple files, the first occurrence is kept

## Original Value Preservation

Normalization preserves the original identifier values so you can trace back to the source data.

### How It Works

When an edge's `subject` or `object` is normalized:

- The **new** (normalized) identifier is written to `subject` or `object`
- The **original** identifier is stored in `original_subject` or `original_object`

### Example

Before normalization:

| subject | object | predicate |
|---------|--------|-----------|
| HGNC:1234 | OMIM:222100 | biolink:gene_associated_with_condition |

After normalization (with OMIM to MONDO mapping):

| subject | object | predicate | original_subject | original_object |
|---------|--------|-----------|------------------|-----------------|
| HGNC:1234 | MONDO:0005148 | biolink:gene_associated_with_condition | NULL | OMIM:222100 |

Note: `original_subject` is NULL because `HGNC:1234` was not in the mappings and was not changed.

### Querying Original Values

You can find all normalized edges:

```sql
SELECT subject, object, original_subject, original_object
FROM edges
WHERE original_subject IS NOT NULL
   OR original_object IS NOT NULL;
```

## Filtering by Mapping Predicate

Normalization rewrites one identifier into another, which only makes sense for mapping predicates
that assert identity. A `skos:exactMatch` row says two identifiers denote the same thing; a
`skos:closeMatch` or `skos:broadMatch` row does not.

### Default Behaviour

By default `normalize` applies **every** mapping row regardless of `predicate_id`. A `broadMatch`
row rewires an edge endpoint exactly as an `exactMatch` row does, collapsing a narrower concept
into a broader one.

When the loaded mappings contain non-exact predicates and no filter is configured, Koza warns and
names the per-predicate counts:

```
⚠️  Applying 20,385 non-exact SSSOM mappings as identity rewrites because use_match is not set
    (skos:broadMatch: 8, skos:closeMatch: 20,377). Set use_match=['skos:exactMatch'] to apply only
    exact matches.
```

### Opting Into a Predicate Filter

Pass `--use-match` (repeatable) to keep only the mapping predicates you want applied:

```bash
# Only identity mappings
koza normalize graph.duckdb -m "mappings/*.sssom.tsv" --use-match skos:exactMatch

# Also accept close matches
koza normalize graph.duckdb -m "mappings/*.sssom.tsv" \
  --use-match skos:exactMatch \
  --use-match skos:closeMatch
```

The same option is available on `koza merge`, and as `use_match` on `NormalizeConfig` and
`MergeConfig`.

Predicates are compared exactly and case-sensitively, as CURIEs:

- Values must have a `prefix:` form. A bare `exactMatch` (or the transform-time `exact`) is
  rejected, because it could never match a `predicate_id`.
- Full IRIs in the SSSOM file or in `--use-match` are contracted to CURIEs for the `skos`, `owl`,
  `rdfs` and `semapv` namespaces, so `http://www.w3.org/2004/02/skos/core#exactMatch` matches
  `skos:exactMatch`.
- If a requested predicate matches no mappings (for example `skos:exactmatch`), or the filter
  removes every mapping that has a `predicate_id`, Koza warns and lists the predicates it found.

### Files Without a predicate_id Column

`predicate_id` is optional in SSSOM. Rows from a file that has no `predicate_id` column are always
kept, even when `--use-match` is set, so such a file keeps working exactly as before. If none of
the loaded files carry the column at all, `--use-match` cannot be enforced and Koza warns rather
than dropping every mapping.

### Blank predicate_id Values

A file that *has* a `predicate_id` column must fill it on every row. A blank value is malformed
SSSOM, so `normalize` fails, whether or not `--use-match` is set. The error names the file, the
number of blank rows, and up to two example `subject_id -> object_id` pairs:

```
Malformed SSSOM file mappings/example.sssom.tsv: 3 row(s) have a blank predicate_id
(e.g. subject_id -> object_id: A:1 -> B:1, A:2 -> B:2). Every row must have a predicate_id
when the column is present.
```

Fix the file by filling in the predicate, or by removing the rows.

## Duplicate Mapping Handling

SSSOM files sometimes contain one-to-many mappings where a single `object_id` maps to multiple `subject_id` values. Koza handles this to prevent edge duplication.

### The Problem

If your SSSOM file contains:

```tsv
subject_id	predicate_id	object_id	mapping_justification
MONDO:0005148	skos:exactMatch	OMIM:222100	semapv:ManualMappingCuration
MONDO:0005149	skos:closeMatch	OMIM:222100	semapv:LexicalMatching
```

Without deduplication, an edge referencing `OMIM:222100` could become two edges.

### How Koza Handles It

Koza keeps only **one mapping per object_id**:

1. Mappings are ordered by source file, then by `subject_id`
2. The first mapping for each `object_id` is kept
3. Subsequent duplicates are discarded with a warning

### Warning Message

When duplicates are detected:

```
Loading SSSOM mappings...
  Loaded 45,678 unique mappings from 2 file(s)
  Found 234 duplicate mappings (one object_id mapped to multiple subject_ids).
  Keeping only one mapping per object_id.
```

### Best Practice

To control which mapping is used, ensure your preferred mappings come first:

1. Order the `--mappings` arguments with preferred files first
2. Or curate your SSSOM files to have one mapping per identifier

## Verification

After normalization, verify the results.

### Check Normalization Statistics

```bash
# Count how many edges were normalized
duckdb graph.duckdb -c "
  SELECT
    COUNT(*) as total_edges,
    COUNT(original_subject) as normalized_subjects,
    COUNT(original_object) as normalized_objects
  FROM edges;
"
```

### Compare Before and After

Save identifiers before normalization for comparison:

```bash
# Before normalization - export unique identifiers
duckdb graph.duckdb -c "
  SELECT DISTINCT object FROM edges WHERE object LIKE 'OMIM:%'
" > before_omim_ids.txt

# Run normalization
koza normalize graph.duckdb -m mondo-omim.sssom.tsv

# After normalization - check OMIM IDs are gone
duckdb graph.duckdb -c "
  SELECT DISTINCT object FROM edges WHERE object LIKE 'OMIM:%'
" > after_omim_ids.txt

# Compare
diff before_omim_ids.txt after_omim_ids.txt
```

### Verify Mapping Coverage

Check which identifiers were not mapped:

```sql
-- Find object identifiers that match a pattern but were not normalized
SELECT DISTINCT object
FROM edges
WHERE object LIKE 'OMIM:%'
  AND original_object IS NULL
LIMIT 20;
```

This shows OMIM IDs that remain in the `object` column (not normalized), likely because they were not in your mapping file.

### Generate a Report

Use `koza report` to get overall statistics after normalization:

```bash
koza report qc -d graph.duckdb -o post_normalize_qc.yaml
```

## Variations

### Using Normalize in the Merge Pipeline

For new graphs, `koza merge` includes normalization as part of its pipeline:

```bash
koza merge \
  --nodes "*.nodes.*" \
  --edges "*.edges.*" \
  --mappings "mappings/*.sssom.tsv" \
  --output merged_graph.duckdb
```

This runs: join -> deduplicate -> **normalize** -> prune

See the [merge command reference](../reference/cli.md#koza-merge) for details.

### Skip Normalization in Merge

If you want to run merge without normalization:

```bash
koza merge \
  --nodes "*.nodes.*" \
  --edges "*.edges.*" \
  --output merged_graph.duckdb \
  --skip-normalize
```

### Normalize After Other Operations

You can run normalize at any point after your database has edges:

```bash
# First, join your files
koza join --nodes "*.nodes.*" --edges "*.edges.*" --output graph.duckdb

# Later, normalize with new mappings
koza normalize graph.duckdb -m new_mappings.sssom.tsv
```

## See Also

- [CLI Reference: normalize](../reference/cli.md#koza-normalize) - Full command options
- [Merge Pipeline](../reference/cli.md#koza-merge) - Complete merge workflow including normalization
- [SSSOM Specification](https://mapping-commons.github.io/sssom/) - Official SSSOM documentation
