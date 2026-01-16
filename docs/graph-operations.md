# Koza Graph Operations Guide

This guide provides comprehensive documentation for Koza's graph operations, designed to work with Knowledge Graph Exchange (KGX) files in multiple formats.

## Overview

Koza graph operations provide powerful tools for manipulating, analyzing, and transforming knowledge graphs stored in KGX format. All operations are built on DuckDB for high performance and support TSV, JSONL, and Parquet formats seamlessly.

### Core Operations

- **[join](#join)** - Combine multiple KGX files into unified database
- **[split](#split)** - Extract subsets with format conversion
- **[prune](#prune)** - Clean graph integrity issues
- **[append](#append)** - Incrementally add data with schema evolution

### Key Principles

1. **Format Agnostic**: All operations work across TSV, JSONL, and Parquet
2. **Schema Flexible**: Automatic harmonization handles column differences
3. **Non-destructive**: Data is moved to archive tables, never deleted
4. **Performance Focused**: DuckDB enables fast processing of large graphs

## Join Operation

The `join` operation combines multiple KGX files into a unified DuckDB database with automatic schema harmonization.

### Basic Usage

```bash
# Join node and edge files from different formats
koza join \
  --nodes genes.tsv proteins.jsonl pathways.parquet \
  --edges gene_protein.tsv protein_pathway.jsonl \
  --output merged_graph.duckdb
```

### Advanced Options

```bash
# Join with comprehensive reporting and progress tracking
koza join \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output graph.duckdb \
  --schema-report \
  --show-progress \
  --quiet
```

### Schema Harmonization

Join automatically handles files with different column schemas:

- **Missing columns**: Filled with NULL values
- **Extra columns**: Preserved in final schema
- **Type conflicts**: Resolved using DuckDB's type inference
- **Multi-valued fields**: Detected and converted to arrays where appropriate

### Output

- **Database file**: DuckDB database with `nodes` and `edges` tables
- **Schema report**: YAML file with detailed schema analysis (if `--schema-report`)
- **CLI summary**: Statistics on files processed, records loaded, schema changes

Example CLI output:
```
✓ Join completed successfully
  📁 Files processed: 6 (6 successful)
  📊 Records loaded: 125,340 nodes, 298,567 edges
  🔄 Schema harmonization: 3 missing columns filled, 2 extra preserved
  📂 Database created: merged_graph.duckdb (4.2 MB)
  ⏱️  Total time: 12.4s
```

## Split Operation

The `split` operation extracts subsets of data from a database with configurable filters and format conversion.

### Basic Usage

```bash
# Split by provided_by field into separate files
koza split \
  --database graph.duckdb \
  --split-on provided_by \
  --output-dir ./split_output
```

### Format Conversion

```bash
# Convert TSV database to Parquet files during split
koza split \
  --database graph.duckdb \
  --split-on category \
  --output-format parquet \
  --output-dir ./parquet_output
```

### Filtering Options

```bash
# Split with custom filters
koza split \
  --database graph.duckdb \
  --split-on namespace \
  --filter-nodes "category='biolink:Gene'" \
  --filter-edges "predicate='biolink:interacts_with'" \
  --output-dir ./filtered_split
```

### Output

Creates separate files for each unique value in the split field:
- `{value}_nodes.{format}`
- `{value}_edges.{format}`

## Prune Operation  

The `prune` operation cleans up graph integrity issues by handling dangling edges and singleton nodes.

### Basic Usage

```bash
# Remove dangling edges, keep singleton nodes
koza prune \
  --database graph.duckdb \
  --keep-singletons
```

### Preview Changes

```bash
# Dry run to preview what would be pruned
koza prune \
  --database graph.duckdb \
  --dry-run \
  --remove-singletons
```

### Singleton Node Strategies

**Keep singletons** (default):
```bash
koza prune --database graph.duckdb --keep-singletons
```

**Remove singletons**:
```bash
koza prune --database graph.duckdb --remove-singletons
```

### Dangling Edge Handling

Dangling edges (pointing to non-existent nodes) are automatically:
1. Identified using LEFT JOIN queries
2. Moved to `dangling_edges` table (not deleted)
3. Categorized by missing subject vs object nodes
4. Reported with source attribution

### Output

Prune creates additional tables for data preservation:
- **`dangling_edges`**: Edges pointing to missing nodes
- **`singleton_nodes`**: Isolated nodes (if `--remove-singletons`)
- **Original tables**: Cleaned of integrity issues

Example CLI output:
```
✓ Graph pruned successfully
  - 156 dangling edges moved to dangling_edges table
  - 23 singleton nodes preserved (--keep-singletons)
  - Main graph: 174,844 connected edges remain
📊 Dangling edges by source:
  - source_a: 89 edges (missing 12 target nodes)
  - source_b: 67 edges (missing 8 target nodes)
```

## Append Operation

The `append` operation adds new data to existing databases with schema evolution and optional deduplication.

### Basic Usage

```bash
# Add new files to existing database
koza append \
  --database existing_graph.duckdb \
  --nodes new_genes.tsv updated_pathways.jsonl \
  --edges new_interactions.parquet
```

### Schema Evolution

```bash
# Append with automatic schema evolution and deduplication
koza append \
  --database graph.duckdb \
  --nodes genes_with_new_fields.tsv \
  --deduplicate \
  --show-progress \
  --schema-report
```

### Schema Evolution Features

- **New columns**: Automatically added to existing tables
- **Backward compatibility**: Existing data gets NULL for new columns
- **Type safety**: DuckDB handles type inference and conversion
- **Change tracking**: Reports all schema modifications

### Deduplication

When `--deduplicate` is enabled:
- Removes exact duplicates by ID field
- Keeps first occurrence of each ID
- Reports number of duplicates removed
- Works on both nodes and edges tables

### Output

Append operation provides detailed change tracking:

Example CLI output:
```
✓ Append completed successfully
  📁 Files processed: 3 (3 successful)
  📊 Records added: 15,234
  🔄 Schema evolution: 2 new columns added
    - Added 1 new columns to nodes: custom_score
    - Added 1 new columns to edges: confidence_value
  🔧 Duplicates removed: 45
  📈 Database growth:
    - Nodes: 125,340 → 138,574 (+13,234)
    - Edges: 298,567 → 300,567 (+2,000)
    - Database: graph.duckdb (4.8 MB)
  ⏱️  Total time: 8.2s
```

## Schema Reporting

All operations support optional schema reporting with `--schema-report` flag.

### Report Contents

Schema reports include:
- **File analysis**: Format detection, column counts, record counts
- **Schema summary**: Unique columns across all files
- **Column details**: Data types, null percentages, example values
- **Format compatibility**: Cross-format column mapping

### Report Formats

**CLI Summary**:
```
📋 Schema Analysis:
  - Nodes: 4 files, 23 unique columns
  - Edges: 2 files, 18 unique columns
📊 Column Coverage:
  - id: 100% (required field)
  - category: 100% (nodes only)
  - predicate: 100% (edges only)
  - custom_score: 25% (extension field)
```

**YAML Report** (saved as `{database_name}_schema_report_{operation}.yaml`):
```yaml
operation: join
timestamp: "2024-01-15T10:30:45"
summary:
  nodes:
    file_count: 4
    unique_columns: 23
    total_records: 125340
  edges:
    file_count: 2  
    unique_columns: 18
    total_records: 298567
files:
  - path: "genes.tsv"
    format: "TSV"
    type: "nodes"
    records: 50000
    columns:
      id: {type: "VARCHAR", null_pct: 0}
      category: {type: "VARCHAR", null_pct: 0}
      # ... additional columns
```

## Multi-Format Support

### Supported Formats

- **TSV**: Tab-separated values (standard KGX format)
- **JSONL**: JSON Lines (one JSON object per line)
- **Parquet**: Columnar format for analytics

### Format Detection

Automatic detection based on:
1. File extension (`.tsv`, `.jsonl`, `.parquet`)
2. Compression support (`.gz`, `.bz2`)
3. Content analysis for ambiguous cases

### Mixed-Format Operations

All operations seamlessly handle mixed formats:

```bash
# Join files in different formats
koza join \
  --nodes genes.tsv proteins.jsonl pathways.parquet \
  --edges interactions.tsv.gz associations.jsonl.bz2 \
  --output mixed_graph.duckdb
```

### Format Conversion

Operations can convert between formats:

```bash
# Convert TSV to Parquet during split
koza split \
  --database tsv_graph.duckdb \
  --split-on provided_by \
  --output-format parquet
```

## Performance Considerations

### Memory Management

- **Streaming**: Large files processed in chunks
- **Lazy evaluation**: Operations chained without intermediate copies  
- **Compression**: Support for compressed inputs reduces I/O

### Query Optimization

- **DuckDB engine**: Vectorized execution and query optimization
- **Columnar storage**: Efficient for analytical workloads
- **Parallel processing**: Multi-threaded operations where possible

### Best Practices

1. **Use compressed files** (`.gz`) to reduce I/O time
2. **Enable progress bars** (`--show-progress`) for long operations
3. **Preview with dry-run** before destructive operations
4. **Monitor disk space** for large join operations
5. **Use Parquet format** for repeated analytical workloads

## Error Handling and Recovery

### Common Issues

**File not found**:
```
Error: File not found: missing_file.tsv
Solution: Verify file paths and permissions
```

**Schema conflicts**:
```
Warning: Type conflict for column 'score' (INTEGER vs VARCHAR)
Resolution: DuckDB will use most permissive type (VARCHAR)
```

**Memory limits**:
```
Error: Out of memory during operation
Solution: Process files in smaller batches or increase system memory
```

### Recovery Strategies

1. **Non-destructive operations**: Original data preserved in archive tables
2. **Transaction safety**: Operations are atomic (all succeed or all fail)  
3. **Backup recommendations**: Copy databases before destructive operations
4. **Logging**: Comprehensive logging for debugging issues

### Data Integrity

All operations maintain referential integrity:
- Dangling edges moved to separate tables (not deleted)
- Schema changes tracked and reversible
- Duplicate data preserved with clear provenance
- Foreign key relationships maintained where possible

## Advanced Usage Examples

### Pipeline Workflows

Chain multiple operations for complete graph processing:

```bash
# Complete graph processing pipeline
koza join \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output raw_graph.duckdb \
  --schema-report

koza prune \
  --database raw_graph.duckdb \
  --keep-singletons

koza append \
  --database raw_graph.duckdb \
  --nodes corrections.tsv \
  --deduplicate

koza split \
  --database raw_graph.duckdb \
  --split-on namespace \
  --output-format parquet \
  --output-dir final_graphs
```

### Configuration Files

Use configuration files for complex operations:

```yaml
# join_config.yaml
nodes:
  - path: "genes.tsv"
    source_name: "gene_source"
  - path: "proteins.jsonl"
    source_name: "protein_source"
edges:
  - path: "interactions.parquet"
    source_name: "interaction_source"
output: "configured_graph.duckdb"
schema_report: true
show_progress: true
```

```bash
koza join --config join_config.yaml
```

### Batch Processing

Process multiple databases in batch:

```bash
# Process all databases in directory
for db in *.duckdb; do
  echo "Processing $db"
  koza prune --database "$db" --keep-singletons --quiet
  koza split --database "$db" --split-on provided_by --output-dir "./split_$(basename $db .duckdb)"
done
```

## Troubleshooting

### Performance Issues

**Slow join operations**:
- Check available memory and disk space
- Use compressed input files
- Consider processing files in smaller batches

**High memory usage**:
- Enable streaming mode (automatic for large files)
- Close other applications during processing
- Use temporary directories on fast storage

### Data Quality Issues  

**Unexpected schema changes**:
- Review schema reports for column additions
- Verify input file consistency
- Check for encoding issues in text files

**Missing data after operations**:
- Check archive tables (`dangling_edges`, `singleton_nodes`)
- Review operation logs for warnings
- Verify input file integrity

### Getting Help

For additional support:
- Check operation-specific help: `koza {operation} --help`
- Review schema reports for data insights
- Enable verbose logging with `--debug` flag
- Consult the [Koza documentation](https://koza.monarchinitiative.org/)

## Migration from cat-merge

For users migrating from cat-merge workflows:

### Equivalent Operations

| cat-merge | Koza Graph Operations |
|-----------|----------------------|
| `merge()` | `koza join` + `koza prune` |
| Directory merge | `koza join --nodes *.nodes.* --edges *.edges.*` |
| Format conversion | `koza split --output-format {format}` |

### Key Improvements

1. **Multi-format support**: No longer limited to TSV
2. **Schema flexibility**: Automatic handling of column differences  
3. **Data preservation**: Non-destructive operations with archiving
4. **Rich CLI**: Progress bars, statistics, and detailed reporting
5. **Incremental updates**: Append operation for database evolution