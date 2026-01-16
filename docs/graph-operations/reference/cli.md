# CLI Reference

Complete documentation for all graph operation CLI commands.

---

## koza join

Combine multiple KGX files into a unified DuckDB database with automatic schema harmonization.

### Synopsis

```bash
koza join [OPTIONS]
```

### Description

The `join` command loads multiple KGX files (TSV, JSONL, or Parquet) into a single DuckDB database. It automatically handles schema differences between files, filling missing columns with NULL values and preserving extra columns. Supports glob patterns for file discovery and automatic file detection from directories.

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--nodes` | `-n` | List[str] | None | Node files or glob patterns (can specify multiple) |
| `--edges` | `-e` | List[str] | None | Edge files or glob patterns (can specify multiple) |
| `--input-dir` | `-d` | Path | None | Directory to auto-discover KGX files |
| `--output` | `-o` | str | None | Path to output database file (default: in-memory) |
| `--format` | `-f` | KGXFormat | `tsv` | Output format for any exported files |
| `--schema-report` | | bool | False | Generate schema compliance report |
| `--progress` | `-p` | bool | True | Show progress bars |
| `--quiet` | `-q` | bool | False | Suppress output |

### Examples

```bash
# Auto-discover files in directory
koza join --input-dir ./data/ -o graph.duckdb

# Use glob patterns for node and edge files
koza join -n "data/*_nodes.tsv" -e "data/*_edges.tsv" -o graph.duckdb

# Mix directory discovery with additional files
koza join --input-dir ./data/ -n extra_nodes.tsv -o graph.duckdb

# Multiple individual files from different formats
koza join -n genes.tsv -n proteins.jsonl -e interactions.parquet -o graph.duckdb

# Generate schema compliance report
koza join -n "*.nodes.*" -e "*.edges.*" -o graph.duckdb --schema-report
```

### Output

- **Database file**: DuckDB database with `nodes` and `edges` tables
- **Schema report**: `{database}_schema_report.yaml` (if `--schema-report` enabled)
- **CLI summary**: File counts, record counts, and schema harmonization details

**See also**: [How to Join KGX Files](../how-to/join-files.md)

---

## koza split

Split a KGX file by specified fields with format conversion support.

### Synopsis

```bash
koza split FILE FIELDS [OPTIONS]
```

### Description

The `split` command extracts subsets of data from a KGX file, creating separate output files for each unique value (or combination of values) in the specified fields. Supports format conversion during split operations.

### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `FILE` | str | Path to the KGX file to split (required) |
| `FIELDS` | str | Comma-separated list of fields to split on (required) |

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output-dir` | `-o` | Path | `./output` | Output directory for split files |
| `--format` | `-f` | KGXFormat | None | Output format (default: preserve input format) |
| `--remove-prefixes` | | bool | False | Remove prefixes from values in filenames |
| `--progress` | `-p` | bool | True | Show progress bars |
| `--quiet` | `-q` | bool | False | Suppress output |

### Examples

```bash
# Split nodes by category
koza split nodes.tsv category -o ./split_output

# Split edges by predicate and convert to Parquet
koza split edges.tsv predicate -o ./parquet_output -f parquet

# Split by multiple fields (creates files per combination)
koza split nodes.tsv namespace,category -o ./split_output

# Remove CURIE prefixes from output filenames
koza split nodes.tsv category --remove-prefixes -o ./clean_output

# Split with progress tracking
koza split large_nodes.tsv provided_by -o ./split_output -p
```

### Output

For each unique value (or combination) in the split fields, creates:
- `{value}_nodes.{format}` or `{value}_edges.{format}` depending on input file type

When splitting on array-type fields (e.g., `category`), records may appear in multiple output files if they have multiple values in that field.

**See also**: [How to Split a Graph](../how-to/split-graph.md)

---

## koza merge

Run the complete merge pipeline: join, deduplicate, normalize, and prune.

### Synopsis

```bash
koza merge [OPTIONS]
```

### Description

The `merge` command orchestrates a complete graph processing pipeline in sequence:

1. **Join**: Load and combine multiple KGX files into a unified database
2. **Deduplicate**: Remove duplicate nodes and edges by ID
3. **Normalize**: Apply SSSOM mappings to edge subject/object references
4. **Prune**: Remove dangling edges and handle singleton nodes

This is the recommended approach for creating a production-ready knowledge graph from multiple sources.

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--nodes` | `-n` | List[str] | None | Node files or glob patterns (can specify multiple) |
| `--edges` | `-e` | List[str] | None | Edge files or glob patterns (can specify multiple) |
| `--mappings` | `-m` | List[str] | None | SSSOM mapping files or glob patterns |
| `--input-dir` | `-d` | Path | None | Directory to auto-discover KGX files |
| `--mappings-dir` | | Path | None | Directory containing SSSOM mapping files |
| `--output` | `-o` | str | None | Path to output database file (default: temporary) |
| `--export` | | bool | False | Export final clean data to files |
| `--export-dir` | | Path | None | Directory for exported files (required if `--export`) |
| `--format` | `-f` | KGXFormat | `tsv` | Output format for exported files |
| `--archive` | | bool | False | Export as archive (tar) instead of loose files |
| `--compress` | | bool | False | Compress archive as tar.gz (requires `--archive`) |
| `--graph-name` | | str | `merged_graph` | Name for graph files in archive |
| `--skip-normalize` | | bool | False | Skip normalization step |
| `--skip-prune` | | bool | False | Skip pruning step |
| `--keep-singletons` | | bool | True | Keep singleton nodes (default) |
| `--remove-singletons` | | bool | False | Move singleton nodes to separate table |
| `--progress` | `-p` | bool | True | Show progress bars |
| `--quiet` | `-q` | bool | False | Suppress output |

### Examples

```bash
# Full pipeline with auto-discovery
koza merge --input-dir ./data/ --mappings-dir ./sssom/ -o clean_graph.duckdb

# Specific files with export to Parquet
koza merge -n nodes.tsv -e edges.tsv -m mappings.sssom.tsv \
  --export --export-dir ./output/ -f parquet

# Skip normalization (no SSSOM mappings needed)
koza merge -n "*.nodes.tsv" -e "*.edges.tsv" --skip-normalize -o graph.duckdb

# Create compressed archive for distribution
koza merge --input-dir ./data/ -m "*.sssom.tsv" \
  --export --export-dir ./dist/ --archive --compress --graph-name my_kg

# Custom singleton handling
koza merge --input-dir ./data/ -m "*.sssom.tsv" --remove-singletons -o graph.duckdb
```

### Output

- **Database file**: DuckDB database with cleaned `nodes` and `edges` tables
- **Archive tables**: `duplicate_nodes`, `duplicate_edges`, `dangling_edges`, `singleton_nodes` (if applicable)
- **Exported files**: KGX files in specified format (if `--export` enabled)
- **CLI summary**: Progress and statistics for each pipeline step

**See also**: [How to Join KGX Files](../how-to/join-files.md), [How to Normalize Identifiers](../how-to/normalize-ids.md), [How to Clean a Graph](../how-to/clean-graph.md)

---

## koza normalize

Apply SSSOM mappings to normalize edge subject/object references.

### Synopsis

```bash
koza normalize DATABASE [OPTIONS]
```

### Description

The `normalize` command loads SSSOM (Simple Standard for Sharing Ontological Mappings) files and applies them to rewrite edge subject and object identifiers to their canonical/equivalent forms. Node identifiers themselves are not changed - only edge references are normalized. Original values are preserved in `original_subject` and `original_object` columns.

### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `DATABASE` | str | Path to existing DuckDB database file (required) |

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--mappings` | `-m` | List[str] | None | SSSOM mapping files or glob patterns (can specify multiple) |
| `--mappings-dir` | `-d` | Path | None | Directory containing SSSOM mapping files |
| `--progress` | `-p` | bool | True | Show progress bars |
| `--quiet` | `-q` | bool | False | Suppress output |

### Examples

```bash
# Apply specific mapping files
koza normalize graph.duckdb -m gene_mappings.sssom.tsv -m mondo.sssom.tsv

# Auto-discover SSSOM files in directory
koza normalize graph.duckdb --mappings-dir ./sssom/

# Apply mappings with glob pattern
koza normalize graph.duckdb -m "mappings/*.sssom.tsv"

# Quiet operation for automation
koza normalize graph.duckdb -m mappings.sssom.tsv -q
```

### Output

- **Modified edges table**: `subject` and `object` columns updated with mapped identifiers
- **Preservation columns**: `original_subject` and `original_object` store pre-normalization values
- **CLI summary**: Count of loaded mappings and normalized references

**Note**: When one `object_id` maps to multiple `subject_id` values in SSSOM files, only the first mapping is kept to prevent edge duplication.

**See also**: [How to Normalize Identifiers](../how-to/normalize-ids.md)

---

## koza deduplicate

Remove duplicate nodes and edges by ID.

### Synopsis

The `deduplicate` operation is included in the `merge` pipeline but is not exposed as a standalone CLI command. Use `koza merge` with appropriate options, or `koza append --deduplicate` for incremental deduplication.

### Description

Deduplication identifies nodes and edges with duplicate IDs, archives all duplicates to separate tables (`duplicate_nodes`, `duplicate_edges`), and keeps only the first occurrence in the main tables. Order is determined by `file_source` or `provided_by` fields.

### Usage via Merge

```bash
# Merge includes deduplication by default
koza merge -n "*.nodes.tsv" -e "*.edges.tsv" --skip-normalize -o graph.duckdb
```

### Usage via Append

```bash
# Deduplicate during append operation
koza append graph.duckdb -n new_nodes.tsv --deduplicate
```

### Archive Tables

After deduplication, inspect removed duplicates:

```sql
-- View duplicate nodes
SELECT * FROM duplicate_nodes LIMIT 10;

-- Count duplicates by source
SELECT file_source, COUNT(*) FROM duplicate_edges GROUP BY file_source;
```

**See also**: [How to Perform Incremental Updates](../how-to/incremental-updates.md)

---

## koza prune

Prune graph by removing dangling edges and handling singleton nodes.

### Synopsis

```bash
koza prune DATABASE [OPTIONS]
```

### Description

The `prune` command cleans up graph integrity issues by identifying and moving dangling edges (edges pointing to non-existent nodes) to a separate table. It can also optionally move singleton nodes (nodes with no edges) to a separate table. Data is never deleted - only moved to archive tables for preservation.

### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `DATABASE` | str | Path to the DuckDB database file to prune (required) |

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--keep-singletons` | | bool | True* | Keep singleton nodes in main table |
| `--remove-singletons` | | bool | False | Move singleton nodes to separate table |
| `--min-component-size` | | int | None | Minimum connected component size (experimental) |
| `--progress` | `-p` | bool | True | Show progress bars |
| `--quiet` | `-q` | bool | False | Suppress output |

*Default behavior: if neither `--keep-singletons` nor `--remove-singletons` is specified, singletons are kept.

### Examples

```bash
# Keep singleton nodes, move dangling edges (default)
koza prune graph.duckdb

# Explicitly keep singletons
koza prune graph.duckdb --keep-singletons

# Remove singleton nodes to separate table
koza prune graph.duckdb --remove-singletons

# Experimental: filter small components
koza prune graph.duckdb --min-component-size 10

# Quiet operation for automation
koza prune graph.duckdb --keep-singletons -q
```

### Output

Creates archive tables for data preservation:
- **`dangling_edges`**: Edges pointing to non-existent nodes
- **`singleton_nodes`**: Isolated nodes (if `--remove-singletons`)
- **CLI summary**: Counts of edges/nodes moved, integrity statistics

**See also**: [How to Clean a Graph](../how-to/clean-graph.md)

---

## koza append

Append new KGX files to an existing graph database.

### Synopsis

```bash
koza append DATABASE [OPTIONS]
```

### Description

The `append` command adds new data to an existing DuckDB database with automatic schema evolution. New columns in appended files are automatically added to existing tables, with existing records receiving NULL values for new columns. Optional deduplication removes exact duplicates after appending.

### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `DATABASE` | str | Path to existing DuckDB database file (required) |

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--nodes` | `-n` | List[str] | None | Node files or glob patterns (can specify multiple) |
| `--edges` | `-e` | List[str] | None | Edge files or glob patterns (can specify multiple) |
| `--input-dir` | `-d` | Path | None | Directory to auto-discover KGX files |
| `--deduplicate` | | bool | False | Remove duplicates during append |
| `--schema-report` | | bool | False | Generate schema compliance report |
| `--progress` | `-p` | bool | True | Show progress bars |
| `--quiet` | `-q` | bool | False | Suppress output |

### Examples

```bash
# Append specific files to existing database
koza append graph.duckdb -n new_nodes.tsv -e new_edges.tsv

# Auto-discover files in directory and append
koza append graph.duckdb --input-dir ./new_data/

# Append with deduplication and schema reporting
koza append graph.duckdb -n "*.tsv" --deduplicate --schema-report

# Multiple files with glob patterns
koza append graph.duckdb -n "batch2/*.nodes.*" -e "batch2/*.edges.*"

# Quiet append for automation
koza append graph.duckdb -n corrections.tsv -q
```

### Output

- **Schema changes**: Reports new columns added and their sources
- **Record counts**: Before/after record counts for nodes and edges
- **Duplicate statistics**: Number of duplicates removed (if `--deduplicate`)
- **Schema report**: Detailed analysis (if `--schema-report`)

**See also**: [How to Perform Incremental Updates](../how-to/incremental-updates.md)

---

## koza report

Generate comprehensive reports for KGX graph databases.

### Synopsis

```bash
koza report REPORT_TYPE --database DATABASE [OPTIONS]
```

### Description

The `report` command generates various analysis reports for graph databases. Three report types are available: QC (quality control), graph-stats (comprehensive statistics), and schema (database schema analysis).

### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `REPORT_TYPE` | str | Type of report: `qc`, `graph-stats`, or `schema` (required) |

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--database` | `-d` | Path | Required | Path to DuckDB database file |
| `--output` | `-o` | Path | None | Path to output report file (YAML format) |
| `--quiet` | `-q` | bool | False | Suppress progress output |

### Report Types

#### qc - Quality Control Report

Generates quality control analysis grouped by data source, including node/edge counts, category distributions, and potential issues.

```bash
koza report qc -d merged.duckdb -o qc_report.yaml
```

#### graph-stats - Graph Statistics Report

Generates comprehensive graph statistics similar to `merged_graph_stats.yaml`, including total counts, degree distributions, and connectivity metrics.

```bash
koza report graph-stats -d merged.duckdb -o graph_stats.yaml
```

#### schema - Schema Report

Analyzes database schema and biolink compliance, reporting column types, coverage, and potential schema issues.

```bash
koza report schema -d merged.duckdb -o schema_report.yaml
```

### Examples

```bash
# Generate QC report with output file
koza report qc -d merged.duckdb -o qc_report.yaml

# Generate graph statistics
koza report graph-stats -d merged.duckdb -o graph_stats.yaml

# Generate schema report
koza report schema -d merged.duckdb -o schema_report.yaml

# Quick QC analysis (console output only)
koza report qc -d merged.duckdb

# Quiet operation for scripts
koza report graph-stats -d merged.duckdb -o stats.yaml -q
```

### Output

All reports are generated in YAML format and include:
- **Timestamp**: When the report was generated
- **Database info**: Source database path and size
- **Statistics**: Type-specific metrics and analysis

**See also**: [How to Generate Reports](../how-to/generate-reports.md)

---

## koza node-report

Generate tabular node reports with categorical column grouping.

### Synopsis

```bash
koza node-report [OPTIONS]
```

### Description

The `node-report` command generates tabular reports showing node counts grouped by categorical columns (namespace, category, provided_by, etc.). Can read from either a DuckDB database or directly from a node file.

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--database` | `-d` | Path | None | Path to DuckDB database file |
| `--file` | `-f` | Path | None | Path to node file (TSV, JSONL, or Parquet) |
| `--output` | `-o` | Path | None | Path to output report file |
| `--format` | | TabularReportFormat | `tsv` | Output format: `tsv`, `jsonl`, or `parquet` |
| `--column` | `-c` | List[str] | None | Categorical columns to group by (can specify multiple) |
| `--quiet` | `-q` | bool | False | Suppress progress output |

**Note**: Must specify either `--database` or `--file`.

### Examples

```bash
# From database with default columns
koza node-report -d merged.duckdb -o node_report.tsv

# From file with Parquet output
koza node-report -f nodes.tsv -o node_report.parquet --format parquet

# Custom categorical columns
koza node-report -d merged.duckdb -o report.tsv -c namespace -c category -c provided_by

# JSONL output format
koza node-report -d merged.duckdb -o node_report.jsonl --format jsonl
```

### Output

Tabular report with columns for each categorical field plus a count column. Default categorical columns include `namespace`, `category`, and `provided_by` when present.

**See also**: [How to Generate Reports](../how-to/generate-reports.md)

---

## koza edge-report

Generate tabular edge reports with denormalized node information.

### Synopsis

```bash
koza edge-report [OPTIONS]
```

### Description

The `edge-report` command generates tabular reports showing edge counts grouped by categorical columns. When node information is available, it joins edges to nodes to include `subject_category` and `object_category` in the grouping.

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--database` | `-d` | Path | None | Path to DuckDB database file |
| `--nodes` | `-n` | Path | None | Path to node file (for denormalization) |
| `--edges` | `-e` | Path | None | Path to edge file (TSV, JSONL, or Parquet) |
| `--output` | `-o` | Path | None | Path to output report file |
| `--format` | | TabularReportFormat | `tsv` | Output format: `tsv`, `jsonl`, or `parquet` |
| `--column` | `-c` | List[str] | None | Categorical columns to group by (can specify multiple) |
| `--quiet` | `-q` | bool | False | Suppress progress output |

**Note**: Must specify either `--database` or `--edges`.

### Examples

```bash
# From database with default columns
koza edge-report -d merged.duckdb -o edge_report.tsv

# From files with Parquet output
koza edge-report -n nodes.tsv -e edges.tsv -o edge_report.parquet --format parquet

# Custom categorical columns
koza edge-report -d merged.duckdb -o report.tsv \
  -c subject_category -c predicate -c object_category -c primary_knowledge_source

# Edge report without node denormalization
koza edge-report -e edges.tsv -o edge_report.tsv
```

### Output

Tabular report with columns for each categorical field plus a count column. When node information is available, includes `subject_category` and `object_category` derived from joining to the nodes table.

**See also**: [How to Generate Reports](../how-to/generate-reports.md)

---

## koza node-examples

Generate sample rows per node type.

### Synopsis

```bash
koza node-examples [OPTIONS]
```

### Description

The `node-examples` command samples N example rows for each distinct value in a type column (default: `category`). Useful for documentation, debugging, and data exploration.

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--database` | `-d` | Path | None | Path to DuckDB database file |
| `--file` | `-f` | Path | None | Path to node file (TSV, JSONL, or Parquet) |
| `--output` | `-o` | Path | None | Path to output examples file |
| `--format` | | TabularReportFormat | `tsv` | Output format: `tsv`, `jsonl`, or `parquet` |
| `--sample-size` | `-n` | int | 5 | Number of examples per type |
| `--type-column` | `-t` | str | `category` | Column to partition examples by |
| `--quiet` | `-q` | bool | False | Suppress progress output |

**Note**: Must specify either `--database` or `--file`.

### Examples

```bash
# From database (5 examples per category)
koza node-examples -d merged.duckdb -o node_examples.tsv

# From file with 10 examples per type
koza node-examples -f nodes.tsv -o examples.tsv -n 10

# Group by different column
koza node-examples -d merged.duckdb -o examples.tsv -t provided_by

# Output as Parquet
koza node-examples -d merged.duckdb -o examples.parquet --format parquet

# More examples per category
koza node-examples -d merged.duckdb -o examples.tsv -n 20
```

### Output

Tabular file containing N sample rows for each unique value in the type column. All node columns are preserved in the output.

**See also**: [How to Generate Reports](../how-to/generate-reports.md)

---

## koza edge-examples

Generate sample rows per edge type.

### Synopsis

```bash
koza edge-examples [OPTIONS]
```

### Description

The `edge-examples` command samples N example rows for each distinct combination of type columns (default: `subject_category`, `predicate`, `object_category`). When node information is available, it joins edges to nodes for category information.

### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--database` | `-d` | Path | None | Path to DuckDB database file |
| `--nodes` | `-n` | Path | None | Path to node file (for denormalization) |
| `--edges` | `-e` | Path | None | Path to edge file (TSV, JSONL, or Parquet) |
| `--output` | `-o` | Path | None | Path to output examples file |
| `--format` | | TabularReportFormat | `tsv` | Output format: `tsv`, `jsonl`, or `parquet` |
| `--sample-size` | `-s` | int | 5 | Number of examples per type |
| `--type-column` | `-t` | List[str] | None | Columns to partition examples by (can specify multiple) |
| `--quiet` | `-q` | bool | False | Suppress progress output |

**Note**: Must specify either `--database` or `--edges`.

### Examples

```bash
# From database (5 examples per edge type)
koza edge-examples -d merged.duckdb -o edge_examples.tsv

# From files with 10 examples
koza edge-examples -n nodes.tsv -e edges.tsv -o examples.tsv -s 10

# Custom type columns
koza edge-examples -d merged.duckdb -o examples.tsv -t predicate -t primary_knowledge_source

# Output as Parquet
koza edge-examples -d merged.duckdb -o examples.parquet --format parquet

# More examples per edge type
koza edge-examples -d merged.duckdb -o examples.tsv -s 20
```

### Output

Tabular file containing N sample rows for each unique combination of type columns. When node information is available, includes `subject_category` and `object_category` columns.

**See also**: [How to Generate Reports](../how-to/generate-reports.md)

---

## Common Patterns

### File Specification Formats

All commands that accept file lists support multiple specification formats:

#### Glob Patterns

```bash
# Match all node files
--nodes "*.nodes.*"

# Match specific formats
--nodes "*.tsv" --edges "*.jsonl"

# Match files in subdirectories
--nodes "data/*_nodes.tsv"
```

#### Multiple Files

```bash
# Specify multiple files individually
--nodes genes.tsv --nodes proteins.tsv --edges interactions.tsv

# Or as a list
--nodes genes.tsv proteins.jsonl pathways.parquet
```

### Progress and Output Control

#### Progress Indicators

- `--progress` / `-p`: Display progress bars (enabled by default for most commands)
- `--quiet` / `-q`: Suppress all non-error output

#### Output Formats

Supported formats for tabular reports and exports:
- **TSV**: Tab-separated values (KGX standard)
- **JSONL**: JSON Lines format
- **Parquet**: Columnar format for analytics

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (file not found, permission denied, etc.) |
| 2 | Invalid arguments or configuration |
| 130 | Interrupted by user (Ctrl+C) |

---

## Getting Help

```bash
# General help
koza --help

# Command-specific help
koza join --help
koza split --help
koza merge --help
koza normalize --help
koza prune --help
koza append --help
koza report --help
koza node-report --help
koza edge-report --help
koza node-examples --help
koza edge-examples --help

# Version information
koza --version
```
