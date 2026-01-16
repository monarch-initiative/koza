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

### Key Columns for Normalization

- **subject_id**: The target identifier (what you want to normalize TO)
- **object_id**: The source identifier (what you want to normalize FROM)
- **predicate_id**: The mapping relationship (e.g., `skos:exactMatch`, `skos:closeMatch`)
- **mapping_justification**: How the mapping was created (optional but recommended)

During normalization, Koza replaces `object_id` values in your edges with the corresponding `subject_id` values.

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
koza normalize \
  --database graph.duckdb \
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
koza normalize \
  --database graph.duckdb \
  --mappings \
    mondo-omim.sssom.tsv \
    mondo-orphanet.sssom.tsv \
    hp-mp.sssom.tsv
```

### Using a Mappings Directory

If all your SSSOM files are in one directory:

```bash
koza normalize \
  --database graph.duckdb \
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
koza normalize --database graph.duckdb --mappings mondo-omim.sssom.tsv

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
koza report qc --database graph.duckdb --output post_normalize_qc.yaml
```

## Variations

### Using Normalize in the Merge Pipeline

The recommended approach for new graphs is to use `koza merge`, which includes normalization:

```bash
koza merge \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --mappings mappings/*.sssom.tsv \
  --output merged_graph.duckdb
```

This runs: join -> deduplicate -> **normalize** -> prune

See the [merge command reference](../reference/cli.md#koza-merge) for details.

### Skip Normalization in Merge

If you want to run merge without normalization:

```bash
koza merge \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output merged_graph.duckdb \
  --skip-normalize
```

### Normalize After Other Operations

You can run normalize at any point after your database has edges:

```bash
# First, join your files
koza join --nodes *.nodes.* --edges *.edges.* --output graph.duckdb

# Later, normalize with new mappings
koza normalize --database graph.duckdb --mappings new_mappings.sssom.tsv
```

## See Also

- [CLI Reference: normalize](../reference/cli.md#koza-normalize) - Full command options
- [Merge Pipeline](../reference/cli.md#koza-merge) - Complete merge workflow including normalization
- [SSSOM Specification](https://mapping-commons.github.io/sssom/) - Official SSSOM documentation
