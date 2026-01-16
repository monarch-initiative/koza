# How to Generate Reports

## Goal

Generate quality control reports, statistics, and data summaries from your knowledge graph databases. Koza provides multiple reporting commands for different analysis needs: QC reports for data quality assessment, graph statistics for structural analysis, schema compliance for biolink validation, and tabular reports for detailed breakdowns.

## Prerequisites

- A DuckDB database created by `koza join`, `koza merge`, or `koza append`
- Alternatively, KGX files (TSV, JSONL, or Parquet) for file-based reports

## QC Report

The `koza report qc` command generates a quality control report with node/edge statistics grouped by data source.

### Basic Usage

```bash
koza report qc -d graph.duckdb -o qc_report.yaml
```

### Console-Only Analysis

For quick QC analysis without saving to a file:

```bash
koza report qc -d graph.duckdb
```

### Output Format

The QC report is saved as YAML with the following structure:

```yaml
summary:
  total_nodes: 125340
  total_edges: 298567
  dangling_edges: 156
  duplicate_nodes: 0
  singleton_nodes: 23
nodes:
  - provided_by: gene_source
    category: biolink:Gene
    count: 50000
  - provided_by: disease_source
    category: biolink:Disease
    count: 25340
edges:
  - provided_by: interaction_source
    predicate: biolink:interacts_with
    count: 150000
  - provided_by: association_source
    predicate: biolink:associated_with
    count: 148567
```

The report helps identify:

- Total entity counts and data distribution
- Potential integrity issues (dangling edges, duplicates)
- Breakdown by source for multi-source graphs

## Graph Statistics

The `koza report graph-stats` command generates comprehensive graph statistics similar to the `merged_graph_stats.yaml` output from cat-merge.

### Basic Usage

```bash
koza report graph-stats -d graph.duckdb -o graph_stats.yaml
```

### Output Format

```yaml
graph_name: Graph Statistics
node_stats:
  total_nodes: 125340
  count_by_category:
    biolink:Gene:
      count: 50000
      provided_by:
        gene_source: 50000
    biolink:Disease:
      count: 25340
      provided_by:
        disease_source: 25340
  count_by_id_prefixes:
    HGNC: 45000
    NCBIGene: 5000
    MONDO: 15340
    OMIM: 10000
  node_categories:
    - biolink:Gene
    - biolink:Disease
    - biolink:Phenotype
  node_id_prefixes:
    - HGNC
    - NCBIGene
    - MONDO
    - OMIM
  provided_by:
    - gene_source
    - disease_source
edge_stats:
  total_edges: 298567
  count_by_predicates:
    biolink:interacts_with:
      count: 150000
      provided_by:
        interaction_source: 150000
    biolink:associated_with:
      count: 148567
      provided_by:
        association_source: 148567
  predicates:
    - biolink:interacts_with
    - biolink:associated_with
  provided_by:
    - interaction_source
    - association_source
```

Statistics generated include:

- Node counts by category and ID prefix
- Edge counts by predicate
- Attribution breakdown by `provided_by` source
- Complete enumeration of categories, predicates, and prefixes

## Schema Compliance

The `koza report schema` command analyzes database schema and checks biolink model compliance.

### Basic Usage

```bash
koza report schema -d graph.duckdb -o schema_report.yaml
```

### Output Format

```yaml
metadata:
  operation: schema_analysis
  generated_at: '2024-01-15 10:30:45'
  report_version: '1.0'
schema_analysis:
  summary:
    nodes:
      file_count: 4
      unique_columns: 23
      all_columns:
        - id
        - category
        - name
        - description
        - xref
        - provided_by
    edges:
      file_count: 2
      unique_columns: 18
      all_columns:
        - id
        - subject
        - predicate
        - object
        - category
        - primary_knowledge_source
  files:
    - filename: genes_nodes.tsv
      table_type: nodes
      column_count: 12
      columns:
        - id
        - category
        - name
        - symbol
```

The schema report helps identify:

- Column coverage across source files
- Schema harmonization applied during join
- Biolink-compliant vs. extension columns
- Data type consistency

## Node Reports

The `koza node-report` command generates tabular reports with node counts grouped by categorical columns.

### From Database

```bash
koza node-report -d graph.duckdb -o node_report.tsv
```

### From File

```bash
koza node-report -f nodes.tsv -o node_report.tsv
```

### Custom Columns

Specify which categorical columns to group by:

```bash
koza node-report -d graph.duckdb -o report.tsv \
    -c namespace -c category -c provided_by
```

### Output Example

```
namespace	category	provided_by	count
HGNC	biolink:Gene	gene_source	45000
NCBIGene	biolink:Gene	gene_source	5000
MONDO	biolink:Disease	disease_source	15340
OMIM	biolink:Disease	disease_source	10000
```

The default grouping columns include `namespace`, `category`, and `provided_by` when present in the data.

## Edge Reports

The `koza edge-report` command generates tabular reports with edge counts, including denormalized node information.

### From Database

```bash
koza edge-report -d graph.duckdb -o edge_report.tsv
```

### From Files

When working with separate node and edge files, provide both for denormalization:

```bash
koza edge-report -n nodes.tsv -e edges.tsv -o edge_report.tsv
```

### Custom Columns

```bash
koza edge-report -d graph.duckdb -o report.tsv \
    -c subject_category -c predicate -c object_category -c primary_knowledge_source
```

### Output Example

```
subject_category	predicate	object_category	primary_knowledge_source	count
biolink:Gene	biolink:interacts_with	biolink:Gene	string_db	85000
biolink:Gene	biolink:interacts_with	biolink:Protein	biogrid	65000
biolink:Disease	biolink:associated_with	biolink:Phenotype	hpo	98567
biolink:Gene	biolink:associated_with	biolink:Disease	disgenet	50000
```

The edge report automatically joins edges to nodes to derive `subject_category` and `object_category` from the referenced nodes.

## Node Examples

The `koza node-examples` command extracts sample nodes for each category or other grouping column.

### Basic Usage

```bash
koza node-examples -d graph.duckdb -o node_examples.tsv
```

### Custom Sample Size

```bash
koza node-examples -d graph.duckdb -o examples.tsv -n 10
```

### Group by Different Column

```bash
koza node-examples -d graph.duckdb -o examples.tsv -t provided_by
```

### From File

```bash
koza node-examples -f nodes.tsv -o examples.tsv -n 5
```

### Output Example

The output contains N sample rows for each distinct value in the type column:

```
id	name	category	provided_by	...
HGNC:1234	BRCA1	biolink:Gene	gene_source	...
HGNC:5678	TP53	biolink:Gene	gene_source	...
MONDO:0005148	diabetes mellitus	biolink:Disease	disease_source	...
MONDO:0004975	Alzheimer disease	biolink:Disease	disease_source	...
```

This is useful for:

- Quick data validation and spot-checking
- Documentation and examples
- Debugging data quality issues

## Edge Examples

The `koza edge-examples` command extracts sample edges for each predicate pattern or custom grouping.

### Basic Usage

```bash
koza edge-examples -d graph.duckdb -o edge_examples.tsv
```

### Custom Sample Size

```bash
koza edge-examples -d graph.duckdb -o examples.tsv -s 10
```

### Custom Type Columns

By default, edges are grouped by `subject_category`, `predicate`, and `object_category`. Customize this:

```bash
koza edge-examples -d graph.duckdb -o examples.tsv \
    -t predicate -t primary_knowledge_source
```

### From Files

```bash
koza edge-examples -n nodes.tsv -e edges.tsv -o examples.tsv -s 5
```

### Output Example

```
subject	predicate	object	subject_name	object_name	primary_knowledge_source	...
HGNC:1234	biolink:interacts_with	HGNC:5678	BRCA1	TP53	string_db	...
HGNC:9999	biolink:interacts_with	HGNC:8888	MYC	MAX	biogrid	...
MONDO:0005148	biolink:associated_with	HP:0001943	diabetes	Hypoglycemia	hpo	...
```

Edge examples help verify:

- Correct subject/object relationships
- Predicate usage patterns
- Knowledge source attribution

## Output Formats

All tabular reports (`node-report`, `edge-report`, `node-examples`, `edge-examples`) support multiple output formats.

### TSV (Default)

```bash
koza node-report -d graph.duckdb -o report.tsv --format tsv
```

### Parquet

For large reports or downstream analytics:

```bash
koza node-report -d graph.duckdb -o report.parquet --format parquet
```

### CSV

```bash
koza node-report -d graph.duckdb -o report.csv --format csv
```

### JSON

```bash
koza node-report -d graph.duckdb -o report.json --format json
```

## Common Options

All report commands support these options:

| Option | Description |
|--------|-------------|
| `-d, --database` | Path to DuckDB database file |
| `-o, --output` | Path to output file |
| `-q, --quiet` | Suppress progress output |

## Workflow Examples

### Complete QC Pipeline

Generate all reports for a merged graph:

```bash
# Generate all report types
koza report qc -d merged.duckdb -o qc_report.yaml
koza report graph-stats -d merged.duckdb -o graph_stats.yaml
koza report schema -d merged.duckdb -o schema_report.yaml

# Generate tabular breakdowns
koza node-report -d merged.duckdb -o node_report.tsv
koza edge-report -d merged.duckdb -o edge_report.tsv

# Extract examples for documentation
koza node-examples -d merged.duckdb -o node_examples.tsv -n 3
koza edge-examples -d merged.duckdb -o edge_examples.tsv -s 3
```

### Post-Merge Validation

After running `koza merge`, validate the results:

```bash
# Check for data quality issues
koza report qc -d merged.duckdb -o post_merge_qc.yaml

# Verify expected categories and predicates
koza report graph-stats -d merged.duckdb -o post_merge_stats.yaml

# Spot-check examples
koza edge-examples -d merged.duckdb -o edge_samples.tsv -s 5
```

## See Also

- [CLI Reference](../reference/cli.md) - Complete command documentation
- [Configuration Reference](../reference/configuration.md) - Report configuration options
- [Data Integrity](../explanation/data-integrity.md) - Understanding archive tables in reports
