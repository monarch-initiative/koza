# How to Join Files

## Goal

Combine multiple KGX files into a unified DuckDB database. The join operation automatically handles schema harmonization across files with different column structures and supports multiple input formats.

## Prerequisites

- Koza installed (`pip install koza`)
- KGX files (nodes and/or edges in TSV, JSONL, or Parquet format)

## Basic Join

The simplest case combines a node file and an edge file into a single database.

```bash
koza join \
  --nodes genes.tsv \
  --edges gene_interactions.tsv \
  --output gene_graph.duckdb
```

This creates `gene_graph.duckdb` containing two tables: `nodes` and `edges`.

### Joining Multiple Files

You can specify multiple files for each table type:

```bash
koza join \
  --nodes genes.tsv proteins.tsv pathways.tsv \
  --edges gene_protein.tsv protein_pathway.tsv \
  --output combined_graph.duckdb
```

## Mixed Formats

The join operation seamlessly handles files in different formats. DuckDB automatically detects formats based on file extensions.

```bash
koza join \
  --nodes genes.tsv proteins.jsonl pathways.parquet \
  --edges interactions.tsv associations.jsonl.gz \
  --output mixed_format_graph.duckdb
```

Supported formats:

- **TSV**: Tab-separated values (`.tsv`, `.tsv.gz`)
- **JSONL**: JSON Lines (`.jsonl`, `.jsonl.gz`, `.jsonl.bz2`)
- **Parquet**: Apache Parquet (`.parquet`)

Compressed files (`.gz`, `.bz2`) are automatically decompressed during processing.

## Using Glob Patterns

For directories with many files following naming conventions, use wildcard patterns:

```bash
# Join all node and edge files
koza join \
  --nodes *.nodes.tsv \
  --edges *.edges.tsv \
  --output graph.duckdb
```

More flexible patterns:

```bash
# Match multiple extensions
koza join \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output graph.duckdb

# Match files in subdirectories
koza join \
  --nodes data/**/nodes.tsv \
  --edges data/**/edges.tsv \
  --output graph.duckdb
```

## Schema Reporting

Use the `--schema-report` flag to generate a detailed YAML report analyzing the schema across all input files:

```bash
koza join \
  --nodes genes.tsv proteins.jsonl \
  --edges interactions.tsv \
  --output graph.duckdb \
  --schema-report
```

This creates `graph_schema_report.yaml` containing:

- **File analysis**: Format detection, column counts, record counts per file
- **Schema summary**: Unique columns across all files
- **Column details**: Data types, null percentages, example values
- **Schema harmonization**: How differences between files were resolved

Schema harmonization handles:

- **Missing columns**: Filled with NULL values
- **Extra columns**: Preserved in the final schema
- **Type conflicts**: Resolved using DuckDB's type inference
- **Multi-valued fields**: Detected and converted to arrays where appropriate

## Generating provided_by

Use `--generate-provided-by` to automatically populate the `provided_by` field based on source filenames:

```bash
koza join \
  --nodes hgnc_genes.tsv uniprot_proteins.tsv \
  --edges string_interactions.tsv \
  --output graph.duckdb \
  --generate-provided-by
```

This sets `provided_by` to the source filename (without extension) for each record, enabling provenance tracking and later splitting by source.

## Persistent vs In-Memory

### Persistent Database (Recommended)

Use `--output` to create a persistent DuckDB file:

```bash
koza join \
  --nodes genes.tsv \
  --edges interactions.tsv \
  --output graph.duckdb
```

Use persistent databases when:

- Processing large datasets
- Running multiple subsequent operations (prune, split, normalize)
- Sharing results with others
- Preserving work for later analysis

### In-Memory Database

Omit `--output` for an in-memory database (useful for quick analysis or piping to other operations):

```bash
koza join \
  --nodes genes.tsv \
  --edges interactions.tsv
```

!!! warning "In-Memory Limitations"
    In-memory databases are lost when the process exits. Always use `--output` for data you want to keep.

## Progress Tracking

For large files, enable progress tracking:

```bash
koza join \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output graph.duckdb \
  --show-progress
```

Combine with `--quiet` to show only progress bars without other output:

```bash
koza join \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output graph.duckdb \
  --show-progress \
  --quiet
```

## Verification

After joining, verify the operation succeeded using SQL queries or the report commands.

### Quick Verification with DuckDB CLI

```bash
duckdb graph.duckdb "SELECT COUNT(*) AS node_count FROM nodes"
duckdb graph.duckdb "SELECT COUNT(*) AS edge_count FROM edges"
```

### Check Schema

```bash
duckdb graph.duckdb "DESCRIBE nodes"
duckdb graph.duckdb "DESCRIBE edges"
```

### Generate QC Report

```bash
koza report qc \
  --database graph.duckdb \
  --output qc_report.yaml
```

### View Sample Records

```bash
duckdb graph.duckdb "SELECT * FROM nodes LIMIT 5"
duckdb graph.duckdb "SELECT * FROM edges LIMIT 5"
```

### Verify Source Attribution

If using `--generate-provided-by`:

```bash
duckdb graph.duckdb "SELECT provided_by, COUNT(*) FROM nodes GROUP BY provided_by"
duckdb graph.duckdb "SELECT provided_by, COUNT(*) FROM edges GROUP BY provided_by"
```

## Complete Example

A typical workflow combining multiple options:

```bash
koza join \
  --nodes data/hgnc_genes.tsv data/uniprot_proteins.jsonl data/reactome_pathways.parquet \
  --edges data/gene_protein_interactions.tsv data/protein_pathway_associations.jsonl \
  --output knowledge_graph.duckdb \
  --generate-provided-by \
  --schema-report \
  --show-progress
```

Expected output:

```
Join completed successfully
  Files processed: 5 (5 successful)
  Records loaded: 125,340 nodes, 298,567 edges
  Schema harmonization: 3 missing columns filled, 2 extra preserved
  Database created: knowledge_graph.duckdb (4.2 MB)
  Total time: 12.4s
```

## Next Steps

After joining files, you might want to:

- [Clean the graph](clean-graph.md) to remove dangling edges
- [Normalize identifiers](normalize-ids.md) using SSSOM mappings
- [Split the graph](split-graph.md) by source or category
- [Generate reports](generate-reports.md) for quality control

## See Also

- [CLI Reference: koza join](../reference/cli.md#koza-join)
- [Schema Handling](../explanation/schema-handling.md) - Format detection and schema harmonization
- [Generate Reports](generate-reports.md) - Schema analysis and QC reporting
