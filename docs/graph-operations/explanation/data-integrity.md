# Data Integrity

## Overview

Koza graph operations follow a philosophy of **non-destructive data operations**. When problems are detected in your graph data, such as duplicate entries, dangling edges, or isolated nodes, the problematic records are never permanently deleted. Instead, they are moved to archive tables where they remain accessible for analysis, debugging, and potential recovery.

This approach recognizes that "problem" data often contains valuable information:

- Duplicates may reveal integration issues between data sources
- Dangling edges may indicate missing node files or ID mismatches
- Singletons may represent valid entities that simply lack relationships in the current dataset

By preserving this data, Koza enables thorough quality control analysis without risking irreversible data loss.

## Move, Don't Delete

The core principle is simple: **move problem data to archive tables rather than deleting it**.

This design choice provides several benefits:

**Enables debugging and QC**: When edges reference non-existent nodes, you can examine the archived edges to understand which nodes are missing and from which source files. This helps identify upstream data issues.

**Supports recovery**: If data is archived incorrectly (perhaps due to misconfiguration or a bug in upstream processing), you can recover it from the archive tables without needing to re-run the entire pipeline.

**Provides audit trail**: Archive tables document exactly what was removed and when. This is essential for reproducibility and for explaining changes between pipeline runs.

**No data loss**: Even aggressive cleaning operations preserve all original data. You can always inspect what was removed and verify that the cleaning logic behaved correctly.

## Archive Tables

Koza creates several archive tables during graph operations. Each serves a specific purpose:

### dangling_edges

Contains edges where the `subject` or `object` ID does not exist in the nodes table.

```sql
-- Example: View dangling edges
SELECT * FROM dangling_edges LIMIT 10;

-- Find which nodes are missing
SELECT DISTINCT subject as missing_node
FROM dangling_edges e
LEFT JOIN nodes n ON e.subject = n.id
WHERE n.id IS NULL;
```

Dangling edges typically indicate:

- Node files that failed to load
- ID mismatches between node and edge files
- Normalization that mapped to non-existent canonical IDs

### duplicate_nodes

Contains all rows that had duplicate IDs in the nodes table. When multiple rows share the same `id`, all of them are copied here, and only the first occurrence (ordered by `file_source`) is kept in the main `nodes` table.

```sql
-- Example: View duplicate nodes
SELECT id, COUNT(*) as occurrence_count
FROM duplicate_nodes
GROUP BY id
ORDER BY occurrence_count DESC;

-- Compare duplicates for a specific ID
SELECT * FROM duplicate_nodes WHERE id = 'HGNC:1234';
```

Duplicate nodes may indicate:

- The same entity appearing in multiple source files
- Version conflicts between data sources
- Intentional overlaps that need resolution

### duplicate_edges

Contains all rows that had duplicate `id` values in the edges table. Similar to `duplicate_nodes`, all duplicates are archived and only the first occurrence is retained.

```sql
-- Example: View duplicate edges by source
SELECT file_source, COUNT(*) as duplicates
FROM duplicate_edges
GROUP BY file_source
ORDER BY duplicates DESC;
```

### singleton_nodes

Contains nodes that do not appear as `subject` or `object` in any edge. This table is only populated when you explicitly request singleton removal with `--remove-singletons`.

```sql
-- Example: Analyze singleton nodes by category
SELECT category, COUNT(*) as count
FROM singleton_nodes
GROUP BY category
ORDER BY count DESC;
```

Singleton nodes may represent:

- Valid entities that simply lack relationships in your dataset
- Nodes from incomplete data sources
- Orphaned entries from failed edge loading

## Provenance Tracking

Koza tracks the source of each record through provenance columns, enabling source-aware deduplication and detailed QC analysis.

### file_source Column

When loading files, Koza adds a `file_source` column containing the source identifier:

```bash
# Source name is derived from filename by default
koza join --nodes gene_nodes.tsv --edges gene_edges.tsv -d graph.duckdb

# Or specify explicitly
koza join --nodes gene_nodes.tsv:gene_source --edges gene_edges.tsv:gene_source -d graph.duckdb
```

The `file_source` column enables:

- Tracking which file each record came from
- Deterministic ordering during deduplication
- Source-specific QC reports

### provided_by Column

The `provided_by` column is a standard KGX provenance field that may already exist in your source data. If present, Koza preserves it. If absent, Koza can generate it from the source name.

### Ordering During Deduplication

When duplicates are found, Koza keeps the "first" occurrence based on ordering by provenance columns:

1. `file_source` (preferred) - Added by Koza during loading
2. `provided_by` (fallback) - Standard KGX provenance column
3. Constant (last resort) - Arbitrary but deterministic ordering

This means you can control which version of a duplicate is kept by ordering your input files appropriately or by setting source names that sort in your preferred order.

## Original Value Preservation

When normalizing identifiers using SSSOM mappings, Koza preserves the original values so you can always trace back to the source data.

### original_subject and original_object Columns

After normalization, edges gain two new columns:

- `original_subject`: The subject ID before normalization (NULL if unchanged)
- `original_object`: The object ID before normalization (NULL if unchanged)

```sql
-- Example: Find edges that were normalized
SELECT subject, original_subject, object, original_object
FROM edges
WHERE original_subject IS NOT NULL
   OR original_object IS NOT NULL;

-- Compare before and after
SELECT
    original_subject as before,
    subject as after,
    COUNT(*) as edge_count
FROM edges
WHERE original_subject IS NOT NULL
GROUP BY original_subject, subject
ORDER BY edge_count DESC;
```

### Benefits of Preserving Originals

- **Debugging**: When an edge seems wrong, you can check what IDs it had before normalization
- **Validation**: Compare normalized IDs against expected mappings
- **Reversibility**: Reconstruct the original graph if needed
- **Provenance**: Full audit trail of transformations applied to each record

## Recovery via SQL

Since archive tables are standard DuckDB tables, you can query them directly and even recover data if needed.

### Query Archive Tables

```sql
-- Connect to the database
-- duckdb graph.duckdb

-- View all archive tables
SHOW TABLES;

-- Count records in each archive
SELECT 'dangling_edges' as table_name, COUNT(*) as count FROM dangling_edges
UNION ALL
SELECT 'duplicate_nodes', COUNT(*) FROM duplicate_nodes
UNION ALL
SELECT 'duplicate_edges', COUNT(*) FROM duplicate_edges
UNION ALL
SELECT 'singleton_nodes', COUNT(*) FROM singleton_nodes;
```

### Re-insert Recovered Data

If you determine that archived data should be restored:

```sql
-- Restore specific dangling edges (perhaps after adding missing nodes)
INSERT INTO edges
SELECT * FROM dangling_edges
WHERE file_source = 'my_source';

-- Restore singleton nodes
INSERT INTO nodes
SELECT * FROM singleton_nodes
WHERE category = 'biolink:Gene';
```

### Analyze Patterns in Problem Data

```sql
-- Find common patterns in dangling edges
SELECT
    file_source,
    COUNT(*) as dangling_count,
    COUNT(DISTINCT subject) as unique_subjects,
    COUNT(DISTINCT object) as unique_objects
FROM dangling_edges
GROUP BY file_source
ORDER BY dangling_count DESC;

-- Identify which source files contribute most duplicates
SELECT
    file_source,
    COUNT(DISTINCT id) as duplicate_ids,
    COUNT(*) as total_duplicate_rows
FROM duplicate_nodes
GROUP BY file_source
ORDER BY duplicate_ids DESC;
```

## Why This Matters

Non-destructive data operations provide critical benefits for production knowledge graph workflows:

### QC Analysis

Archive tables are a goldmine for quality control:

```sql
-- Generate a QC summary
SELECT
    (SELECT COUNT(*) FROM nodes) as active_nodes,
    (SELECT COUNT(*) FROM edges) as active_edges,
    (SELECT COUNT(*) FROM dangling_edges) as dangling_edges,
    (SELECT COUNT(*) FROM duplicate_nodes) as duplicate_node_rows,
    (SELECT COUNT(*) FROM singleton_nodes) as singleton_nodes;
```

### Debugging Data Issues

When something looks wrong in your graph, archive tables help answer:

- Why are certain edges missing? (Check `dangling_edges`)
- Why is this node's data different than expected? (Check `duplicate_nodes`)
- Why are some entities disconnected? (Check `singleton_nodes`)

### Compliance and Auditing

For regulated environments or reproducible science:

- **Full provenance**: Every record can be traced to its source file
- **Complete audit trail**: Archive tables document all removals
- **Reproducibility**: Re-running with the same inputs produces the same outputs
- **Transparency**: QC reports based on archive tables explain exactly what was cleaned

### Safe Iteration

Non-destructive operations make it safe to iterate on your pipeline:

- Try aggressive cleaning, inspect results, adjust parameters
- Compare archive table contents between runs
- Recover from mistakes without re-running upstream processing

This philosophy ensures that Koza graph operations are both powerful and safe, enabling you to clean and transform your data with confidence.
