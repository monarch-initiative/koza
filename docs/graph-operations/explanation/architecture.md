# Architecture

## Overview

The graph operations module is built on a DuckDB-based architecture that provides high-performance analytical processing for knowledge graphs. At its core is the `GraphDatabase` class, which manages DuckDB connections and provides a unified interface for loading, transforming, and exporting graph data.

The architecture follows a pipeline pattern where data flows through discrete stages: loading into temporary tables, combining with schema-flexible unions, processing (normalization, deduplication, pruning), and finally export or persistence.

## Why DuckDB?

DuckDB was chosen as the foundation for graph operations for several compelling reasons:

**Columnar storage for analytics workloads**: Knowledge graph operations involve scanning and aggregating large datasets - counting nodes by category, grouping edges by predicate, or identifying duplicates. DuckDB's columnar storage excels at these analytical queries, providing significant performance advantages over row-oriented databases.

**SQL interface for flexibility**: Using SQL allows complex graph operations to be expressed declaratively. Operations like finding dangling edges, applying identifier mappings, or generating QC reports can be written as straightforward SQL queries that are easy to understand and modify.

**In-memory and persistent modes**: DuckDB supports both in-memory databases (for quick, temporary processing) and persistent files (for iterative workflows). This flexibility allows users to choose the appropriate mode for their use case without changing their code.

**Excellent performance with large files**: DuckDB can directly read TSV, JSONL, and Parquet files without requiring a separate loading step. Its parallel query execution and efficient compression make it well-suited for multi-gigabyte knowledge graphs.

**No external server needed**: DuckDB runs as an embedded library, eliminating the need to install, configure, or manage a separate database server. This simplifies deployment and makes the tools accessible to users without database administration experience.

## In-Memory vs Persistent

The `GraphDatabase` class supports two operating modes:

### In-memory mode

```python
# Create an in-memory database
with GraphDatabase() as db:
    # All data is temporary
    pass
```

Use in-memory mode when:

- Performing one-off transformations or analyses
- Processing data that fits comfortably in RAM
- You don't need to preserve intermediate results
- Running in environments with limited disk space

### Persistent mode

```python
# Create or open a persistent database
with GraphDatabase(db_path=Path("my_graph.duckdb")) as db:
    # Data persists after the context exits
    pass
```

Use persistent mode when:

- Working with large graphs that benefit from DuckDB's disk-based storage
- Building iterative pipelines where you want to inspect intermediate results
- Running multiple operations over time and want to avoid reloading source files
- Generating QC reports from a database created by a previous operation

## Processing Pipeline

Data flows through the system in a well-defined pipeline:

### 1. Load files into temporary tables

Each input file is loaded into a uniquely-named temporary table. During loading:

- Format is auto-detected from file extension (`.tsv`, `.jsonl`, `.parquet`)
- A `file_source` column tracks which file each record came from
- A `provided_by` column is optionally generated for provenance tracking
- Pipe-delimited fields are automatically converted to arrays for multivalued properties

```python
result = db.load_file(file_spec, generate_provided_by=True)
# Creates temp table like: temp_nodes_my_source_12345678
```

### 2. Combine with UNION ALL BY NAME

After loading all files, temporary tables are combined into final `nodes` and `edges` tables using DuckDB's `UNION ALL BY NAME`. This approach:

- Handles schema differences gracefully (files with different columns are merged, with NULL for missing values)
- Preserves all columns from all input files
- Avoids the need to pre-define a fixed schema

```sql
CREATE TABLE nodes AS
    SELECT * FROM temp_nodes_file1
    UNION ALL BY NAME
    SELECT * FROM temp_nodes_file2
    UNION ALL BY NAME
    SELECT * FROM temp_nodes_file3
```

### 3. Process (normalize, deduplicate, prune)

Once data is in the database, various operations can be applied:

- **Normalize**: Apply SSSOM mappings to harmonize identifiers in edge references
- **Deduplicate**: Remove duplicate nodes and edges, archiving them for QC analysis
- **Prune**: Identify and move dangling edges and optionally singleton nodes

Each operation modifies the main tables in place and may populate archive tables for later inspection.

### 4. Export or persist

Finally, data can be exported back to file formats:

```python
# Export to individual files
db.export_to_format("nodes", output_path, KGXFormat.TSV)

# Export to a tar archive
db.export_to_archive(archive_path, "my_graph", KGXFormat.TSV, compress=True)

# Export to loose files
db.export_to_loose_files(output_dir, "my_graph", KGXFormat.PARQUET)
```

## GraphDatabase Context Manager

The `GraphDatabase` class implements the context manager protocol (`__enter__` and `__exit__`) for safe resource management:

```python
with GraphDatabase(db_path=Path("graph.duckdb")) as db:
    # Connection is automatically managed
    db.load_file(file_spec)
    stats = db.get_stats()
# Connection is automatically closed, even if an exception occurs
```

### Read-only mode

For operations that only query data (like generating reports), the database can be opened in read-only mode:

```python
with GraphDatabase(db_path, read_only=True) as db:
    # Safe for concurrent readers
    stats = db.get_stats()
    qc_report = generate_qc_report(config)
```

Read-only mode:

- Allows multiple concurrent readers on the same database file
- Prevents accidental modifications during reporting
- Is required when you want to query a database while another process might be writing

### Automatic setup

When opened in read-write mode (the default), `GraphDatabase` automatically initializes the database schema, creating necessary tables like `file_schemas` for tracking loaded file metadata. Main data tables (`nodes`, `edges`) are created dynamically when files are loaded, preserving whatever columns exist in the source data.

## Table Structure

The database uses a consistent table structure across operations:

### Main tables

| Table | Description |
|-------|-------------|
| `nodes` | Primary node data with all columns from source files |
| `edges` | Primary edge data with all columns from source files |
| `mappings` | SSSOM mappings for identifier normalization (created during normalize) |

### Archive tables

Archive tables store records that were removed from main tables during QC operations, allowing later investigation:

| Table | Description |
|-------|-------------|
| `dangling_edges` | Edges where subject or object doesn't exist in nodes table |
| `duplicate_nodes` | Nodes with duplicate IDs (all but the first occurrence) |
| `duplicate_edges` | Edges with duplicate (subject, predicate, object) combinations |
| `singleton_nodes` | Nodes not referenced by any edge (when `--remove-singletons` is used) |

### Metadata tables

| Table | Description |
|-------|-------------|
| `file_schemas` | Column information for each loaded file, used for schema analysis |

## SQL Access

Since the underlying storage is DuckDB, you can query the database directly using any DuckDB client or the Python API:

### Using the DuckDB CLI

```bash
duckdb my_graph.duckdb

-- Count nodes by category
SELECT category, COUNT(*) as count
FROM nodes
GROUP BY category
ORDER BY count DESC;

-- Find edges with specific predicates
SELECT subject, predicate, object
FROM edges
WHERE predicate = 'biolink:interacts_with'
LIMIT 10;

-- Analyze dangling edges
SELECT
    split_part(subject, ':', 1) as subject_prefix,
    COUNT(*) as count
FROM dangling_edges
GROUP BY 1
ORDER BY 2 DESC;
```

### Using Python

```python
import duckdb

conn = duckdb.connect("my_graph.duckdb", read_only=True)

# Run custom analytics
result = conn.execute("""
    SELECT
        provided_by,
        COUNT(DISTINCT id) as node_count,
        COUNT(DISTINCT category) as category_count
    FROM nodes
    GROUP BY provided_by
""").fetchdf()

print(result)
conn.close()
```

### Using the GraphDatabase connection

Within operations or custom scripts, you can access the underlying DuckDB connection:

```python
with GraphDatabase(db_path) as db:
    # Access the raw DuckDB connection
    result = db.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()
    print(f"Total nodes: {result[0]}")
```

This direct SQL access provides flexibility for custom analyses, ad-hoc queries, and integration with other tools that support DuckDB.
