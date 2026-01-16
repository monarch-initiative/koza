# How to Do Incremental Updates

## Goal

Add new data to an existing DuckDB database with automatic schema evolution. The `append` operation lets you incrementally grow your knowledge graph without rebuilding from scratch, automatically handling schema differences between old and new data.

## Prerequisites

- An existing DuckDB database (created via `koza join`, `koza merge`, or a previous `koza append`)
- New KGX files to append (nodes and/or edges in TSV, JSONL, or Parquet format)
- Koza installed and available in your PATH

## Basic Append

The simplest append adds new node and edge files to an existing database.

```bash
koza append \
  --database existing_graph.duckdb \
  --nodes new_genes.tsv \
  --edges new_interactions.tsv
```

You can append multiple files at once:

```bash
koza append \
  --database existing_graph.duckdb \
  --nodes new_genes.tsv updated_pathways.jsonl additional_proteins.parquet \
  --edges new_interactions.tsv new_associations.jsonl
```

### Mixed Format Support

Like other Koza operations, append handles mixed formats seamlessly:

```bash
koza append \
  --database graph.duckdb \
  --nodes genes.tsv proteins.jsonl pathways.parquet \
  --edges interactions.tsv.gz associations.jsonl.bz2
```

## Schema Evolution

When new files contain columns that do not exist in the database, append automatically adds these columns to the schema.

```bash
koza append \
  --database graph.duckdb \
  --nodes genes_with_new_fields.tsv \
  --edges interactions_with_confidence.tsv \
  --schema-report
```

### How Schema Evolution Works

1. **New columns detected**: Append compares incoming file schemas with existing table schemas
2. **Columns added**: New columns are added to the database tables using `ALTER TABLE`
3. **Backward compatibility**: Existing rows get NULL values for the new columns
4. **Type safety**: DuckDB handles type inference and conversion automatically

### Example Output

```
Append completed successfully
  Files processed: 2 (2 successful)
  Records added: 15,234
  Schema evolution: 2 new columns added
    - Added 1 new column to nodes: custom_score
    - Added 1 new column to edges: confidence_value
  Database growth:
    - Nodes: 125,340 -> 138,574 (+13,234)
    - Edges: 298,567 -> 300,567 (+2,000)
  Total time: 8.2s
```

## Deduplication During Append

When appending data that may overlap with existing records, use the `--deduplicate` flag to remove duplicates:

```bash
koza append \
  --database graph.duckdb \
  --nodes updated_genes.tsv \
  --edges updated_interactions.tsv \
  --deduplicate
```

### How Deduplication Works

1. **Append first**: New data is added to the tables
2. **Identify duplicates**: Records with the same ID are identified
3. **Keep first occurrence**: The first occurrence (by load order) is kept
4. **Archive duplicates**: Duplicate records are moved to `duplicate_nodes` and `duplicate_edges` tables

### Example with Deduplication

```bash
koza append \
  --database graph.duckdb \
  --nodes genes_v2.tsv \
  --deduplicate \
  --show-progress
```

Output:

```
Append completed successfully
  Files processed: 1 (1 successful)
  Records added: 5,234
  Duplicates removed: 45
  Database: graph.duckdb (4.8 MB)
  Total time: 4.1s
```

!!! info "Deduplication Preserves Data"
    Duplicate records are moved to archive tables (`duplicate_nodes`, `duplicate_edges`), not deleted. You can inspect these tables to understand what was deduplicated.

## Tracking Schema Changes

Use the `--schema-report` flag to generate a detailed report of schema changes:

```bash
koza append \
  --database graph.duckdb \
  --nodes new_data.tsv \
  --schema-report
```

This creates a YAML file (e.g., `graph_schema_report_append.yaml`) containing:

- **File analysis**: Format detection, column counts, record counts per file
- **Schema changes**: List of new columns added to each table
- **Column details**: Data types, null percentages, example values

### Inspecting Schema Changes via SQL

After appending, you can also check the schema directly:

```bash
# View current table schemas
duckdb graph.duckdb "DESCRIBE nodes"
duckdb graph.duckdb "DESCRIBE edges"

# Check which columns have NULL values (potentially new columns)
duckdb graph.duckdb "SELECT COUNT(*) - COUNT(custom_score) as nulls FROM nodes"
```

## When to Use Append vs Join

Choose the right operation based on your use case:

| Scenario | Use Append | Use Join |
|----------|------------|----------|
| Adding new data to existing database | Yes | No |
| Preserving existing database state | Yes | No (overwrites) |
| Incremental daily/weekly updates | Yes | No |
| Full rebuild from all sources | No | Yes |
| Starting fresh with new data | No | Yes |
| Schema evolution needed | Yes (automatic) | Yes (automatic) |
| Combining many files initially | No | Yes |

### Append Use Cases

- **Daily data ingestion**: Add new records from a data pipeline each day
- **Incremental updates**: Add corrections or updates without full rebuild
- **Data augmentation**: Add new sources to an existing graph
- **Schema extension**: Add new properties to existing entities

### Join Use Cases

- **Initial graph creation**: Combine multiple source files into a new database
- **Full rebuild**: Replace existing data with a fresh build from sources
- **Format conversion**: Load data into DuckDB for the first time

### Complete Pipeline Comparison

**Incremental approach (append):**
```bash
# Initial build
koza join --nodes *.nodes.* --edges *.edges.* --output graph.duckdb

# Later: add new data
koza append --database graph.duckdb --nodes new_data.tsv --deduplicate
koza append --database graph.duckdb --nodes more_data.tsv --deduplicate
```

**Full rebuild approach (join):**
```bash
# Rebuild everything each time
koza merge \
  --nodes *.nodes.* new_data.tsv more_data.tsv \
  --edges *.edges.* \
  --output graph.duckdb
```

## Verification

After appending, verify the operation succeeded.

### Check Record Counts

```bash
# Compare before and after counts
duckdb graph.duckdb "SELECT COUNT(*) AS node_count FROM nodes"
duckdb graph.duckdb "SELECT COUNT(*) AS edge_count FROM edges"
```

### Verify New Data Is Present

```bash
# Check for records from the new source
duckdb graph.duckdb "SELECT COUNT(*) FROM nodes WHERE file_source LIKE '%new_data%'"

# Or by provided_by if set
duckdb graph.duckdb "SELECT provided_by, COUNT(*) FROM nodes GROUP BY provided_by ORDER BY COUNT(*) DESC"
```

### Check Schema Evolution

```bash
# View the current schema
duckdb graph.duckdb "DESCRIBE nodes"

# Check for new columns with mostly NULL values (recently added)
duckdb graph.duckdb "
SELECT
    column_name,
    COUNT(*) - COUNT(column_name) as null_count,
    COUNT(*) as total_count
FROM nodes
UNPIVOT (value FOR column_name IN (*))
GROUP BY column_name
ORDER BY null_count DESC
"
```

### Verify Deduplication (if used)

```bash
# Check duplicate archive tables
duckdb graph.duckdb "SELECT COUNT(*) as duplicate_nodes FROM duplicate_nodes"
duckdb graph.duckdb "SELECT COUNT(*) as duplicate_edges FROM duplicate_edges"

# View sample duplicates
duckdb graph.duckdb "SELECT * FROM duplicate_nodes LIMIT 5"
```

### Generate QC Report

For comprehensive verification:

```bash
koza report qc --database graph.duckdb --output qc_report.yaml
```

## Complete Example

A typical incremental update workflow:

```bash
# Step 1: Initial graph build
koza merge \
  --nodes source_a.nodes.tsv source_b.nodes.tsv \
  --edges source_a.edges.tsv source_b.edges.tsv \
  --output knowledge_graph.duckdb

# Step 2: Check initial counts
duckdb knowledge_graph.duckdb "SELECT COUNT(*) FROM nodes"
# Returns: 125340

# Step 3: Append new data with deduplication and schema tracking
koza append \
  --database knowledge_graph.duckdb \
  --nodes new_source_c.nodes.tsv \
  --edges new_source_c.edges.tsv \
  --deduplicate \
  --schema-report \
  --show-progress

# Step 4: Verify the update
duckdb knowledge_graph.duckdb "SELECT COUNT(*) FROM nodes"
# Returns: 138574

# Step 5: Generate updated QC report
koza report qc --database knowledge_graph.duckdb --output qc_report.yaml
```

## See Also

- [CLI Reference: koza append](../reference/cli.md#koza-append)
- [How to Join Files](join-files.md) - Creating the initial database
- [How to Clean Graphs](clean-graph.md) - Deduplication and pruning operations
- [Schema Reporting](../../graph-operations.md#schema-reporting) - Detailed schema analysis
