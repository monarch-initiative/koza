# How to Split Graphs

## Goal

Divide a graph into subsets based on field values with optional format conversion. This is useful for:

- Separating nodes or edges by data source (`provided_by`)
- Creating category-specific subsets (`category`)
- Partitioning large graphs for parallel processing
- Converting between formats (TSV, JSONL, Parquet) during extraction

## Prerequisites

- A KGX file to split (TSV, JSONL, or Parquet format)
- Knowledge of which field(s) to split on (e.g., `provided_by`, `category`, `predicate`)

## Output Filename Pattern

Split generates output filenames automatically using this pattern:

```
{input_basename}_{field_value}_{nodes|edges}.{format}
```

For example, splitting `monarch_nodes.tsv` by `provided_by` where one value is `infores:hgnc` produces:

```
monarch_infores_hgnc_nodes.tsv
```

The field value has special characters (like `:`) replaced with underscores.

## Split by Single Field

The most common use case is splitting by a single field like `provided_by` or `category`.

### Split nodes by source

```bash
koza split monarch_nodes.tsv provided_by --output-dir ./split_by_source
```

This creates one file per unique `provided_by` value in `./split_by_source/`:

- `monarch_infores_hgnc_nodes.tsv` (nodes where `provided_by` = `infores:hgnc`)
- `monarch_infores_omim_nodes.tsv` (nodes where `provided_by` = `infores:omim`)
- `monarch_infores_mondo_nodes.tsv` (nodes where `provided_by` = `infores:mondo`)

### Split edges by predicate

```bash
koza split monarch_edges.tsv predicate --output-dir ./split_by_predicate
```

Output files are named `{input}_{predicate_value}_edges.tsv`:

```
split_by_predicate/
  monarch_biolink_has_phenotype_edges.tsv
  monarch_biolink_causes_edges.tsv
  monarch_biolink_interacts_with_edges.tsv
  ...
```

## Split by Multiple Fields

Split on multiple fields by providing a comma-separated list. Records are grouped by the unique combination of all specified field values.

```bash
koza split monarch_edges.tsv predicate,provided_by --output-dir ./split_multi
```

This creates files for each unique combination:

```
split_multi/
  monarch_biolink_has_phenotype_infores_hpoa_edges.tsv
  monarch_biolink_causes_infores_mondo_edges.tsv
  ...
```

## Format Conversion

Convert between formats during the split operation using the `--format` option.

### Convert TSV to Parquet

```bash
koza split monarch_nodes.tsv provided_by \
  --output-dir ./parquet_split \
  --format parquet
```

### Convert to JSONL

```bash
koza split monarch_edges.tsv predicate \
  --output-dir ./jsonl_split \
  --format jsonl
```

Supported formats:

- `tsv` - Tab-separated values (KGX standard)
- `jsonl` - JSON Lines (one JSON object per line)
- `parquet` - Apache Parquet (columnar, efficient for analytics)

If `--format` is not specified, the output format matches the input format.

## Handling Multivalued Fields

When splitting on array-type fields (like `category` or `provided_by` which can contain multiple values), records may appear in multiple output files.

For example, if a node has:

```json
{
  "id": "HGNC:1234",
  "category": ["biolink:Gene", "biolink:NamedThing"]
}
```

This node will appear in both:

- `monarch_Gene_nodes.tsv`
- `monarch_NamedThing_nodes.tsv`

With this behavior, every record appears in every subset it belongs to.

The split operation automatically detects array fields and uses appropriate filtering (via `list_contains()`) to handle them correctly.

## Prefix Removal

Use `--remove-prefixes` to strip CURIE prefixes from field values when generating filenames.

### Without prefix removal (default)

```bash
koza split monarch_nodes.tsv provided_by --output-dir ./output
```

Output: `monarch_infores_hgnc_nodes.tsv`

### With prefix removal

```bash
koza split monarch_nodes.tsv provided_by \
  --output-dir ./output \
  --remove-prefixes
```

Output: `monarch_hgnc_nodes.tsv`

This option applies when:

- Field values use common prefixes like `infores:`, `biolink:`, or `HP:`
- Shorter filenames are needed
- Files should be organized by the local part of the identifier

## Output Directory

Specify a custom output location with `--output-dir`:

```bash
# Output to current directory
koza split data.tsv provided_by --output-dir .

# Output to nested directory (created if it doesn't exist)
koza split data.tsv category --output-dir ./processed/split/by_category

# Absolute path
koza split data.tsv provided_by --output-dir /data/graphs/split
```

The output directory is created automatically if it does not exist.

## Verification

After splitting, verify the operation completed successfully.

### Check output files exist

```bash
ls -la ./split_output/
```

### Count records across all split files

For TSV files:

```bash
# Count total lines (excluding headers)
wc -l ./split_output/*.tsv | tail -1

# Compare to original
wc -l original_nodes.tsv
```

Note: When splitting on multivalued fields, the total across split files may exceed the original count since records can appear in multiple outputs.

### Verify specific split

```bash
# Check a specific split file
head -5 ./split_output/monarch_hgnc_nodes.tsv

# Verify records have the expected field value
grep "infores:hgnc" ./split_output/monarch_hgnc_nodes.tsv | head -3
```

### Use DuckDB for detailed verification

```bash
# Load and inspect a split file
duckdb -c "SELECT COUNT(*) FROM read_csv_auto('./split_output/monarch_hgnc_nodes.tsv')"

# Verify field values
duckdb -c "SELECT DISTINCT provided_by FROM read_csv_auto('./split_output/monarch_hgnc_nodes.tsv')"
```

## CLI Options Reference

| Option | Short | Description |
|--------|-------|-------------|
| `--output-dir` | `-o` | Output directory for split files (default: `./output`) |
| `--format` | `-f` | Output format: `tsv`, `jsonl`, or `parquet` (default: preserve input) |
| `--remove-prefixes` | | Remove CURIE prefixes from values in filenames |
| `--progress` | `-p` | Show progress bars (default: enabled) |
| `--quiet` | `-q` | Suppress output messages |

## See Also

- [CLI Reference](../reference/cli.md) - Complete CLI documentation
- [How to Join Files](join-files.md) - Combine split files back together
- [How to Export Formats](export-formats.md) - More on format conversion
