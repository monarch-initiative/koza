# Build Your First Graph

Welcome to graph operations! In this tutorial, you will create a simple knowledge graph from scratch, explore it with SQL queries, and export it to files. By the end, you will understand the core workflow that powers more advanced graph processing pipelines.

## What You Will Learn

- Create sample KGX node and edge files
- Join files into a DuckDB database
- Explore your graph with SQL queries
- Generate statistics and reports
- Export to different formats

## Prerequisites

Before starting, ensure you have:

- **Koza installed**: `pip install koza`
- **DuckDB CLI** (optional but recommended): Install from [duckdb.org](https://duckdb.org/docs/installation/) or `pip install duckdb`
- **Basic command line familiarity**

Verify your installation:

```bash
koza --version
```

You should see the Koza version number printed.

## Sample Data

We will create a small knowledge graph about genes and diseases. The graph will have:

- **5 nodes**: 3 genes and 2 diseases
- **5 edges**: Gene-disease associations

This is a tiny example, but the same commands work identically on graphs with millions of nodes and edges.

### Understanding KGX Format

KGX (Knowledge Graph Exchange) is a standard format for biomedical knowledge graphs. It uses:

- **Nodes file**: Contains entities (genes, diseases, phenotypes, etc.)
- **Edges file**: Contains relationships between entities

Both are tab-separated files with specific columns. The minimum required columns are:

- Nodes: `id`, `category`, `name`
- Edges: `id`, `subject`, `predicate`, `object`

## Step 1: Create Sample Files

Let us create our sample data files. You can copy-paste these commands into your terminal, or create the files manually in a text editor.

### Create a working directory

```bash
mkdir -p kgx-tutorial
cd kgx-tutorial
```

### Create the nodes file

Create a file named `sample_nodes.tsv` with the following content:

```bash
cat > sample_nodes.tsv << 'EOF'
id	category	name	description	provided_by
HGNC:1100	biolink:Gene	BRCA1	BRCA1 DNA repair associated	infores:hgnc
HGNC:1101	biolink:Gene	BRCA2	BRCA2 DNA repair associated	infores:hgnc
HGNC:7881	biolink:Gene	NOTCH1	notch receptor 1	infores:hgnc
MONDO:0007254	biolink:Disease	breast cancer	A malignant neoplasm of the breast	infores:mondo
MONDO:0005070	biolink:Disease	leukemia	Cancer of blood-forming tissues	infores:mondo
EOF
```

### Create the edges file

Create a file named `sample_edges.tsv` with the following content:

```bash
cat > sample_edges.tsv << 'EOF'
id	subject	predicate	object	primary_knowledge_source	provided_by
uuid:1	HGNC:1100	biolink:gene_associated_with_condition	MONDO:0007254	infores:clinvar	infores:clinvar
uuid:2	HGNC:1101	biolink:gene_associated_with_condition	MONDO:0007254	infores:clinvar	infores:clinvar
uuid:3	HGNC:7881	biolink:gene_associated_with_condition	MONDO:0005070	infores:clinvar	infores:clinvar
uuid:4	HGNC:1100	biolink:interacts_with	HGNC:1101	infores:string	infores:string
uuid:5	HGNC:1100	biolink:interacts_with	HGNC:7881	infores:string	infores:string
EOF
```

### Verify the files

Check that your files look correct:

```bash
head sample_nodes.tsv
head sample_edges.tsv
```

You should see the header row followed by data rows for each file.

## Step 2: Join Into a Database

Now we will combine these files into a DuckDB database. DuckDB is a fast, embedded analytical database that makes querying your graph data easy and efficient.

### Run the join command

```bash
koza join \
  --nodes sample_nodes.tsv \
  --edges sample_edges.tsv \
  --output my_graph.duckdb
```

You should see output similar to:

```
Join operation completed successfully!
```

The command creates `my_graph.duckdb` containing two tables:

- `nodes` - All your node records
- `edges` - All your edge records

### What just happened?

The `koza join` command:

1. Read both input files
2. Detected the TSV format automatically
3. Inferred column types from the data
4. Created a DuckDB database with optimized storage
5. Loaded all records into `nodes` and `edges` tables

This same process works seamlessly with:

- Mixed file formats (TSV, JSONL, Parquet)
- Multiple input files per table
- Compressed files (.gz, .bz2)
- Files with different column schemas (missing columns are filled with NULL)

## Step 3: Explore with SQL

One of the great benefits of using DuckDB is that you can query your graph using standard SQL. Let us explore our data.

### Count nodes and edges

```bash
duckdb my_graph.duckdb "SELECT COUNT(*) AS node_count FROM nodes"
```

Output:
```
┌────────────┐
│ node_count │
│   int64    │
├────────────┤
│          5 │
└────────────┘
```

```bash
duckdb my_graph.duckdb "SELECT COUNT(*) AS edge_count FROM edges"
```

Output:
```
┌────────────┐
│ edge_count │
│   int64    │
├────────────┤
│          5 │
└────────────┘
```

### View the database schema

See what columns are available:

```bash
duckdb my_graph.duckdb "DESCRIBE nodes"
```

Output:
```
┌─────────────┬─────────────┬─────────┬─────────┬─────────┬─────────┐
│ column_name │ column_type │  null   │   key   │ default │  extra  │
│   varchar   │   varchar   │ varchar │ varchar │ varchar │ varchar │
├─────────────┼─────────────┼─────────┼─────────┼─────────┼─────────┤
│ id          │ VARCHAR     │ YES     │         │         │         │
│ category    │ VARCHAR     │ YES     │         │         │         │
│ name        │ VARCHAR     │ YES     │         │         │         │
│ description │ VARCHAR     │ YES     │         │         │         │
│ provided_by │ VARCHAR     │ YES     │         │         │         │
└─────────────┴─────────────┴─────────┴─────────┴─────────┴─────────┘
```

### List all categories

See what types of entities are in your graph:

```bash
duckdb my_graph.duckdb "SELECT DISTINCT category FROM nodes"
```

Output:
```
┌─────────────────┐
│    category     │
│     varchar     │
├─────────────────┤
│ biolink:Gene    │
│ biolink:Disease │
└─────────────────┘
```

### Count nodes by category

```bash
duckdb my_graph.duckdb "SELECT category, COUNT(*) AS count FROM nodes GROUP BY category"
```

Output:
```
┌─────────────────┬───────┐
│    category     │ count │
│     varchar     │ int64 │
├─────────────────┼───────┤
│ biolink:Gene    │     3 │
│ biolink:Disease │     2 │
└─────────────────┴───────┘
```

### Find specific nodes

Search for nodes by name:

```bash
duckdb my_graph.duckdb "SELECT id, name FROM nodes WHERE name LIKE '%BRCA%'"
```

Output:
```
┌───────────┬───────┐
│    id     │ name  │
│  varchar  │ varchar│
├───────────┼───────┤
│ HGNC:1100 │ BRCA1 │
│ HGNC:1101 │ BRCA2 │
└───────────┴───────┘
```

### Explore edge relationships

List all predicate types:

```bash
duckdb my_graph.duckdb "SELECT predicate, COUNT(*) AS count FROM edges GROUP BY predicate"
```

Output:
```
┌─────────────────────────────────────────┬───────┐
│                predicate                │ count │
│                 varchar                 │ int64 │
├─────────────────────────────────────────┼───────┤
│ biolink:gene_associated_with_condition  │     3 │
│ biolink:interacts_with                  │     2 │
└─────────────────────────────────────────┴───────┘
```

### Find edges for a specific node

What diseases are associated with BRCA1?

```bash
duckdb my_graph.duckdb "
SELECT e.predicate, n.name AS disease_name
FROM edges e
JOIN nodes n ON e.object = n.id
WHERE e.subject = 'HGNC:1100'
  AND e.predicate = 'biolink:gene_associated_with_condition'
"
```

Output:
```
┌────────────────────────────────────────┬───────────────┐
│               predicate                │ disease_name  │
│                varchar                 │    varchar    │
├────────────────────────────────────────┼───────────────┤
│ biolink:gene_associated_with_condition │ breast cancer │
└────────────────────────────────────────┴───────────────┘
```

## Step 4: Generate Statistics

Koza provides built-in commands for generating reports about your graph. These are especially useful for quality control when working with larger datasets.

### Generate graph statistics

```bash
koza report graph-stats --database my_graph.duckdb --output graph_stats.yaml
```

This creates a YAML file with comprehensive statistics:

```bash
cat graph_stats.yaml
```

The report includes:

- Total node and edge counts
- Counts by category and predicate
- Namespace distributions
- Data source breakdowns

### Generate a QC report

The QC (Quality Control) report provides more detailed analysis:

```bash
koza report qc --database my_graph.duckdb --output qc_report.yaml
```

This report helps identify potential data quality issues like:

- Missing required fields
- Orphan nodes (nodes not connected to any edges)
- Invalid identifiers

### View report summary

You can also run reports without saving to a file to see output in the terminal:

```bash
koza report graph-stats --database my_graph.duckdb
```

## Step 5: Export to Files

After working with your graph in the database, you may want to export it back to files. The `split` command can export your entire graph or create subsets based on field values.

### Export all nodes and edges

First, let us export the complete graph. The simplest approach is to split on a field where all records have the same value, or to use a field that groups naturally.

Export nodes by source:

```bash
koza split sample_nodes.tsv provided_by --output-dir ./export
```

This creates separate files for each data source:

```bash
ls -la ./export/
```

Output:
```
sample_infores_hgnc_nodes.tsv
sample_infores_mondo_nodes.tsv
```

### Convert to different formats

You can convert between formats during export. Convert to Parquet (a columnar format ideal for analytics):

```bash
koza split sample_nodes.tsv category \
  --output-dir ./parquet_export \
  --format parquet
```

Or convert to JSONL (JSON Lines, useful for streaming):

```bash
koza split sample_edges.tsv predicate \
  --output-dir ./jsonl_export \
  --format jsonl
```

### Check exported files

Verify the exports look correct:

```bash
# Check Parquet files
ls ./parquet_export/

# Read a Parquet file with DuckDB
duckdb -c "SELECT * FROM read_parquet('./parquet_export/sample_Gene_nodes.parquet')"

# Check JSONL files
ls ./jsonl_export/
head ./jsonl_export/*.jsonl
```

## What You Learned

Congratulations! You have completed the core graph operations workflow. Here is what you accomplished:

1. **Created KGX files** - You made sample node and edge files in the standard KGX TSV format

2. **Joined files into a database** - The `koza join` command combined your files into an efficient DuckDB database that supports fast SQL queries

3. **Explored with SQL** - You queried your graph to:
   - Count nodes and edges
   - List categories and predicates
   - Find specific entities
   - Traverse relationships

4. **Generated reports** - You used `koza report` to create statistics and quality control reports

5. **Exported data** - You used `koza split` to export subsets in different formats (TSV, Parquet, JSONL)

### Key Commands Summary

| Command | Purpose |
|---------|---------|
| `koza join` | Combine KGX files into a DuckDB database |
| `koza report graph-stats` | Generate graph statistics |
| `koza report qc` | Generate quality control report |
| `koza split` | Export/split graph by field values |

## Next Steps

Now that you understand the basics, explore more advanced capabilities:

### Continue Learning

- **[Complete Merge Workflow](merge-pipeline.md)** - Learn to combine data from multiple sources, normalize identifiers with SSSOM mappings, and clean your graph in one pipeline

### How-to Guides

- **[Join Files](../how-to/join-files.md)** - Advanced joining with glob patterns, mixed formats, and schema reporting
- **[Split Graphs](../how-to/split-graph.md)** - More splitting options including prefix removal and multivalued fields
- **[Generate Reports](../how-to/generate-reports.md)** - All available report types and customization options
- **[Normalize IDs](../how-to/normalize-ids.md)** - Use SSSOM mappings to harmonize identifiers
- **[Clean Graphs](../how-to/clean-graph.md)** - Remove duplicates and dangling edges

### Reference

- **[CLI Reference](../reference/cli.md)** - Complete documentation for all commands and options

## Cleanup

When you are done experimenting, you can remove the tutorial files:

```bash
cd ..
rm -rf kgx-tutorial
```

Or keep them around to continue exploring!

---

You now have the foundational knowledge to work with knowledge graphs using Koza. The same patterns you learned here scale to handle real-world graphs with millions of nodes and edges. Happy graphing!
