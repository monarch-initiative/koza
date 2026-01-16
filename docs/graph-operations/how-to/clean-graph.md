# How to Clean Graphs

## Goal

Remove duplicates, dangling edges, and optionally singleton nodes from your knowledge graph. This guide covers the cleanup operations that ensure graph integrity while preserving data through non-destructive archiving.

## Prerequisites

- A DuckDB database containing your graph (created via `koza join`, `koza merge`, or `koza append`)
- Koza installed and available in your PATH

## Removing Dangling Edges

Dangling edges are edges that reference nodes which do not exist in the graph. This commonly occurs when:

- Node and edge files come from different sources with incomplete overlap
- Data has been filtered or subset, leaving orphaned edge references
- There are ID mismatches between node definitions and edge references

Use the `prune` command to identify and remove dangling edges:

```bash
koza prune --database graph.duckdb --keep-singletons
```

### How It Works

The prune operation:

1. Identifies edges where the `subject` does not match any node `id`
2. Identifies edges where the `object` does not match any node `id`
3. Moves these dangling edges to the `dangling_edges` archive table
4. Reports statistics on what was found and moved

### Example Output

```
Prune completed successfully
  - 156 dangling edges moved to dangling_edges table
  - 23 singleton nodes preserved (--keep-singletons)
  - Main graph: 174,844 connected edges remain
Dangling edges by source:
  - source_a: 89 edges (missing 12 target nodes)
  - source_b: 67 edges (missing 8 target nodes)
```

!!! info "Non-Destructive Operation"
    Dangling edges are **moved** to the `dangling_edges` table, not deleted. You can always inspect or recover this data later.

## Handling Singleton Nodes

Singleton nodes are nodes that have no edges connecting them to other nodes. Depending on your use case, you may want to keep or remove them.

### Keep Singletons (Default)

Use `--keep-singletons` to preserve isolated nodes in your graph:

```bash
koza prune --database graph.duckdb --keep-singletons
```

This is useful when:

- Nodes have value on their own (e.g., ontology terms, reference data)
- You plan to add edges later that will connect these nodes
- You want to preserve all node metadata regardless of connectivity

### Remove Singletons

Use `--remove-singletons` to move isolated nodes to an archive table:

```bash
koza prune --database graph.duckdb --remove-singletons
```

This is useful when:

- You only want nodes that participate in relationships
- You are optimizing for graph traversal queries
- Isolated nodes represent incomplete or low-quality data

When singletons are removed, they are moved to the `singleton_nodes` table for later inspection.

## Deduplicating Nodes

The `deduplicate` command removes duplicate nodes that share the same `id`, keeping only the first occurrence.

```bash
koza deduplicate --database graph.duckdb --nodes
```

### How It Works

1. Nodes are grouped by their `id` field
2. For duplicate IDs, the first occurrence is kept (ordered by `file_source` or `provided_by`)
3. All other occurrences are moved to the `duplicate_nodes` archive table

This is important when:

- Multiple source files define the same node with potentially different attributes
- You have appended data that overlaps with existing nodes
- You need deterministic, unique node records

## Deduplicating Edges

The `deduplicate` command can also remove duplicate edges:

```bash
koza deduplicate --database graph.duckdb --edges
```

### How It Works

1. Edges are grouped by their `id` field (or by subject-predicate-object if no ID)
2. For duplicates, the first occurrence is kept
3. All other occurrences are moved to the `duplicate_edges` archive table

To deduplicate both nodes and edges in one command:

```bash
koza deduplicate --database graph.duckdb --nodes --edges
```

## Inspecting Archived Data

All cleanup operations preserve data in archive tables. You can inspect these using SQL queries.

### View Dangling Edges

```sql
-- Connect to the database
-- duckdb graph.duckdb

-- View sample of dangling edges
SELECT * FROM dangling_edges LIMIT 10;

-- Count dangling edges by source
SELECT
    file_source,
    COUNT(*) as count
FROM dangling_edges
GROUP BY file_source
ORDER BY count DESC;

-- Find which nodes are missing
SELECT DISTINCT subject
FROM dangling_edges
WHERE subject NOT IN (SELECT id FROM nodes);
```

### View Duplicate Nodes

```sql
-- View sample of duplicate nodes
SELECT * FROM duplicate_nodes LIMIT 10;

-- Count duplicates by category
SELECT
    category,
    COUNT(*) as duplicate_count
FROM duplicate_nodes
GROUP BY category
ORDER BY duplicate_count DESC;

-- See all versions of a specific duplicated node
SELECT * FROM duplicate_nodes WHERE id = 'MONDO:0005148';
```

### View Duplicate Edges

```sql
-- View sample of duplicate edges
SELECT * FROM duplicate_edges LIMIT 10;

-- Count duplicates by predicate
SELECT
    predicate,
    COUNT(*) as duplicate_count
FROM duplicate_edges
GROUP BY predicate
ORDER BY duplicate_count DESC;
```

### View Singleton Nodes (if removed)

```sql
-- View sample of singleton nodes
SELECT * FROM singleton_nodes LIMIT 10;

-- Count singletons by category
SELECT
    category,
    COUNT(*) as singleton_count
FROM singleton_nodes
GROUP BY category
ORDER BY singleton_count DESC;
```

## Combined Cleanup with Merge

For a complete cleanup pipeline, the `merge` command combines all cleanup operations in sequence:

```bash
koza merge \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output clean_graph.duckdb
```

The merge pipeline runs: **join -> deduplicate -> normalize -> prune**

### Selective Steps

You can skip steps you do not need:

```bash
# Skip normalization (no SSSOM mappings needed)
koza merge \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output clean_graph.duckdb \
  --skip-normalize

# Skip deduplication
koza merge \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output clean_graph.duckdb \
  --skip-deduplicate

# Skip pruning
koza merge \
  --nodes *.nodes.* \
  --edges *.edges.* \
  --output clean_graph.duckdb \
  --skip-prune
```

### Example Merge Output

```
Starting merge pipeline...
Pipeline: join -> deduplicate -> normalize -> prune
Output database: clean_graph.duckdb
Step 1: Join - Loading input files...
Join completed: 6 files | 125,340 nodes | 298,567 edges
Step 2: Deduplicate - Removing duplicate nodes/edges...
Deduplicate completed: 45 duplicate nodes, 123 duplicate edges removed
Step 3: Normalize - Applying SSSOM mappings...
Normalize completed: 3 mapping files | 15,234 edge references normalized
Step 4: Prune - Cleaning graph structure...
Prune completed: 156 dangling edges moved | 23 singleton nodes handled
Merge pipeline completed successfully!
```

## Verification

After cleanup, verify your graph integrity with reports.

### Generate QC Report

```bash
koza report qc --database graph.duckdb --output qc_report.yaml
```

This will show:

- Total node and edge counts
- Breakdown by source/category/predicate
- Any remaining integrity issues

### Generate Graph Statistics

```bash
koza report graph-stats --database graph.duckdb --output graph_stats.yaml
```

### Check Archive Tables

Verify archive tables exist and contain expected data:

```sql
-- Check what archive tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_name IN ('dangling_edges', 'duplicate_nodes', 'duplicate_edges', 'singleton_nodes');

-- Get counts from each archive table
SELECT 'dangling_edges' as table_name, COUNT(*) as count FROM dangling_edges
UNION ALL
SELECT 'duplicate_nodes', COUNT(*) FROM duplicate_nodes
UNION ALL
SELECT 'duplicate_edges', COUNT(*) FROM duplicate_edges;
```

### Verify No Dangling Edges Remain

```sql
-- This should return 0 rows after prune
SELECT COUNT(*) as dangling_count
FROM edges e
LEFT JOIN nodes n1 ON e.subject = n1.id
LEFT JOIN nodes n2 ON e.object = n2.id
WHERE n1.id IS NULL OR n2.id IS NULL;
```

## See Also

- [CLI Reference](../reference/cli.md) - Complete command documentation
- [How to Join Files](join-files.md) - Creating the initial database
- [How to Normalize IDs](normalize-ids.md) - SSSOM-based identifier normalization
- [How to Generate Reports](generate-reports.md) - QC and statistics reporting
