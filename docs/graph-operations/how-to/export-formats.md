# How to Export Formats

## Goal

Export graph data to TSV, JSONL, or Parquet format with optional archiving. This is useful for:

- Sharing graph data with collaborators or downstream tools
- Converting between formats for different analysis workflows
- Creating distributable archives for data releases
- Preparing data for analytics platforms that prefer Parquet

## Prerequisites

- A DuckDB database containing graph data (created via `koza join` or `koza merge`)
- Target directory for exported files

## Export to TSV

TSV (Tab-Separated Values) is the standard KGX format, widely supported by knowledge graph tools.

### Using split for simple export

The `split` command can export an entire graph without splitting when you export all records:

```bash
koza split graph.duckdb id --output-dir ./export --format tsv
```

### Using merge with export

The most common approach is to use `merge` with export options, which processes and exports in one step:

```bash
koza merge \
  --nodes *.nodes.tsv \
  --edges *.edges.tsv \
  --output graph.duckdb \
  --export \
  --export-dir ./output \
  --format tsv
```

This creates:

```
output/
  merged_graph_nodes.tsv
  merged_graph_edges.tsv
```

## Export to JSONL

JSON Lines format stores one JSON object per line, useful for streaming and JavaScript-based tools.

```bash
koza merge \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output graph.duckdb \
  --export \
  --export-dir ./output \
  --format jsonl
```

Output:

```
output/
  merged_graph_nodes.jsonl
  merged_graph_edges.jsonl
```

JSONL is suited for:

- Working with JavaScript or Node.js applications
- Streaming large files line by line
- Preserving complex nested structures
- Integration with document databases

## Export to Parquet

Parquet is a columnar format optimized for analytical workloads and large datasets.

```bash
koza merge \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output graph.duckdb \
  --export \
  --export-dir ./output \
  --format parquet
```

Output:

```
output/
  merged_graph_nodes.parquet
  merged_graph_edges.parquet
```

Parquet supports:

- Large-scale analytics with tools like Spark, Pandas, or Polars
- Storage with automatic compression
- Column-based queries (selecting specific fields)
- Integration with data warehouses and cloud analytics platforms

## Creating Archives

Use the `--archive` flag to bundle exported files into a tar archive:

```bash
koza merge \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output graph.duckdb \
  --export \
  --export-dir ./output \
  --archive
```

This creates a single archive file:

```
output/
  merged_graph.tar
```

The archive contains the nodes and edges files in the specified format (TSV by default).

Archives are useful for:

- Data releases and distribution
- Preserving file relationships
- Single-file management and transfer
- Versioned snapshots of graph data

## Compressed Archives

Add `--compress` to create a gzip-compressed tar archive:

```bash
koza merge \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output graph.duckdb \
  --export \
  --export-dir ./output \
  --archive \
  --compress
```

This creates:

```
output/
  merged_graph.tar.gz
```

Compressed archives reduce file size, especially for TSV and JSONL formats. Parquet files are already compressed internally, so the size reduction is smaller.

!!! note "Compression requires archive"
    The `--compress` flag requires `--archive` to be enabled. You cannot create a compressed archive without first enabling archiving.

## Custom Graph Naming

Use `--graph-name` to specify custom names for exported files:

```bash
koza merge \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output graph.duckdb \
  --export \
  --export-dir ./output \
  --graph-name monarch_kg_2024_01
```

Output with custom naming:

```
output/
  monarch_kg_2024_01_nodes.tsv
  monarch_kg_2024_01_edges.tsv
```

Or with archiving:

```bash
koza merge \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output graph.duckdb \
  --export \
  --export-dir ./output \
  --graph-name monarch_kg_2024_01 \
  --archive \
  --compress
```

Creates: `output/monarch_kg_2024_01.tar.gz`

Custom naming is useful for:

- Version-specific releases (`monarch_kg_v2024_01`)
- Environment identification (`kg_production`, `kg_staging`)
- Source attribution (`hgnc_gene_graph`)
- Date-stamped snapshots

## Loose Files vs Archives

Choose the appropriate export strategy based on your use case.

### Use Loose Files When

- Directly loading into analysis tools (Pandas, R, DuckDB)
- Incremental updates to individual files
- Quick inspection and validation
- Development and testing workflows

```bash
koza merge \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output graph.duckdb \
  --export \
  --export-dir ./output
```

### Use Archives When

- Creating official data releases
- Distributing to external users
- Long-term storage and backup
- Ensuring file integrity during transfer

```bash
koza merge \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output graph.duckdb \
  --export \
  --export-dir ./releases \
  --graph-name monarch_kg_v2024_01 \
  --archive \
  --compress
```

### Use Compressed Archives When

- Minimizing storage costs
- Transferring over networks
- Publishing to data repositories
- Creating distributable packages

## Using merge for Export

The `merge` command combines data processing with export in a single pipeline.

### Complete Pipeline with Export

```bash
koza merge \
  --nodes data/*.nodes.tsv \
  --edges data/*.edges.tsv \
  --mappings sssom/*.sssom.tsv \
  --output processed_graph.duckdb \
  --export \
  --export-dir ./release \
  --graph-name my_knowledge_graph \
  --format parquet \
  --archive \
  --compress
```

This runs the complete pipeline (join, deduplicate, normalize, prune) and exports the final clean data.

### Export-Only Merge

If you only want to export from an existing database, you can skip all processing steps:

```bash
koza merge \
  --nodes empty.tsv \
  --edges empty.tsv \
  --output existing_graph.duckdb \
  --skip-normalize \
  --skip-prune \
  --skip-deduplicate \
  --export \
  --export-dir ./output
```

### Selective Pipeline with Export

Run specific pipeline steps and export:

```bash
# Join and deduplicate only, then export
koza merge \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output graph.duckdb \
  --skip-normalize \
  --skip-prune \
  --export \
  --export-dir ./output \
  --format tsv
```

## CLI Options Reference

| Option | Description |
|--------|-------------|
| `--export` | Enable export of final data to files |
| `--export-dir` | Directory for exported files (required with `--export`) |
| `--format`, `-f` | Output format: `tsv`, `jsonl`, or `parquet` (default: `tsv`) |
| `--archive` | Export as tar archive instead of loose files |
| `--compress` | Compress archive as tar.gz (requires `--archive`) |
| `--graph-name` | Custom name for graph files (default: `merged_graph`) |

## Verification

After exporting, verify the output files.

### Check exported files

```bash
ls -la ./output/
```

### Verify record counts

For TSV:

```bash
wc -l ./output/*_nodes.tsv ./output/*_edges.tsv
```

For Parquet (using DuckDB):

```bash
duckdb -c "SELECT COUNT(*) FROM read_parquet('./output/*_nodes.parquet')"
duckdb -c "SELECT COUNT(*) FROM read_parquet('./output/*_edges.parquet')"
```

### Inspect archive contents

```bash
# List tar contents
tar -tvf ./output/my_graph.tar

# List compressed tar contents
tar -tzvf ./output/my_graph.tar.gz
```

### Validate exported data

```bash
# Check first few records
head -5 ./output/my_graph_nodes.tsv

# For JSONL, validate JSON structure
head -1 ./output/my_graph_nodes.jsonl | jq .
```

## See Also

- [CLI Reference](../reference/cli.md) - Complete CLI documentation
- [How to Join Files](join-files.md) - Creating DuckDB databases to export from
- [How to Split Graphs](split-graph.md) - Alternative export with field-based splitting
- [Schema Handling](../explanation/schema-handling.md) - Format details and type inference
