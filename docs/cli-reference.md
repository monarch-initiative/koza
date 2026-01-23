# Koza CLI Reference

Complete reference for all Koza command-line interface commands and options.

## Global Options

### Version Information
```bash
koza --version
```
Display the current Koza version and exit.

---

## Commands

### transform

Transform biomedical data sources into KGX format using semi-declarative Python transforms.

#### Synopsis
```bash
# Config file mode (traditional)
koza transform CONFIG.yaml [OPTIONS]

# Config-free mode with Python transform (input files as positional args)
koza transform TRANSFORM.py [OPTIONS] [INPUT_FILES]...
```

#### Arguments
- `CONFIG_OR_TRANSFORM` (required) - Configuration YAML file OR Python transform file
- `INPUT_FILES` (optional, variadic) - Input files (supports shell glob expansion)
  - **Config-free mode** (`.py` file): Required. These files are processed by the transform.
  - **Config file mode** (`.yaml` file): Optional. If provided, overrides the `files` list in the config's reader section.

#### Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output-dir` | `-o` | str | `./output` | Path to output directory |
| `--output-format` | `-f` | OutputFormat | `tsv` | Output format (`tsv`, `jsonl`, `parquet`) |
| `--input-format` | | InputFormat | auto | Input format (auto-detected from extension if not specified) |
| `--delimiter` | `-d` | str | auto | Field delimiter for CSV/TSV (default: tab for .tsv, comma for .csv) |
| `--limit` | `-n` | int | 0 | Number of rows to process (0 = all) |
| `--progress` | `-p` | bool | False | Display progress bar during transform |
| `--quiet` | `-q` | bool | False | Suppress output except errors |

#### Examples
```bash
# Basic transform with config file
koza transform examples/string/protein-links-detailed.yaml

# Transform with custom output directory and format
koza transform config.yaml -o ./results -f jsonl

# Transform with progress and row limit
koza transform config.yaml --progress --limit 1000

# Config-free mode with Python transform file (input files at end)
koza transform transform.py -o ./output -f jsonl data/*.yaml

# Config-free mode with explicit input format
koza transform transform.py --input-format yaml data/*.dat
```

---

### join

Combine multiple KGX files into a unified DuckDB database with automatic schema harmonization.

#### Synopsis
```bash
koza join [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--nodes` | List[str] | None | Node files to join (supports glob patterns) |
| `--edges` | List[str] | None | Edge files to join (supports glob patterns) |
| `--input-dir` | Path | None | Directory containing KGX files (auto-discovers) |
| `--output` | str | `joined_graph.duckdb` | Output DuckDB database path |
| `--schema-report` | bool | False | Generate detailed schema analysis report |
| `--show-progress` | bool | False | Display progress bars during loading |
| `--quiet` | bool | False | Suppress all output except errors |

#### File Specification Formats

**Simple paths**:
```bash
koza join --nodes genes.tsv proteins.jsonl --edges interactions.parquet
```

**With source names**:
```bash
koza join --nodes "genes:genes.tsv" "proteins:proteins.jsonl"
```

**Glob patterns**:
```bash
koza join --nodes "*.nodes.*" --edges "*.edges.*"
```

#### Examples
```bash
# Basic join with mixed formats
koza join \
  --nodes genes.tsv proteins.jsonl pathways.parquet \
  --edges gene_protein.tsv protein_pathway.jsonl \
  --output unified_graph.duckdb

# Join with schema reporting and progress
koza join \
  --nodes "*.nodes.*" \
  --edges "*.edges.*" \
  --schema-report \
  --show-progress

# Auto-discover files in directory
koza join --input-dir ./kgx_files --output merged.duckdb

# Quiet operation for scripts
koza join --nodes "*.nodes.tsv" --edges "*.edges.tsv" --quiet
```

#### Output
- **Database file**: DuckDB database with `nodes` and `edges` tables
- **Schema report**: `{output}_schema_report_join.yaml` (if `--schema-report`)
- **CLI summary**: Files processed, records loaded, schema harmonization details

---

### split

Extract subsets of data from a DuckDB database with configurable filters and format conversion.

#### Synopsis
```bash
koza split [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--database` | Path | Required | Input DuckDB database path |
| `--split-on` | str | Required | Column to split on (creates separate files per value) |
| `--output-dir` | Path | `./split_output` | Directory for output files |
| `--output-format` | KGXFormat | `tsv` | Output format (`tsv`, `jsonl`, `parquet`) |
| `--filter-nodes` | str | None | SQL WHERE clause for filtering nodes |
| `--filter-edges` | str | None | SQL WHERE clause for filtering edges |
| `--show-progress` | bool | False | Display progress bars during export |
| `--quiet` | bool | False | Suppress all output except errors |

#### Examples
```bash
# Split by source with original format
koza split --database graph.duckdb --split-on provided_by

# Split with format conversion to Parquet
koza split \
  --database graph.duckdb \
  --split-on namespace \
  --output-format parquet \
  --output-dir ./parquet_output

# Split with custom filters
koza split \
  --database graph.duckdb \
  --split-on category \
  --filter-nodes "namespace='HGNC'" \
  --filter-edges "predicate='biolink:interacts_with'"

# Split with progress tracking
koza split \
  --database large_graph.duckdb \
  --split-on provided_by \
  --show-progress
```

#### Output
For each unique value in the split column, creates:
- `{value}_nodes.{format}` - Node data for that value
- `{value}_edges.{format}` - Edge data for that value

---

### prune

Clean up graph integrity issues by handling dangling edges and singleton nodes.

#### Synopsis
```bash
koza prune [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--database` | Path | Required | DuckDB database to prune |
| `--keep-singletons` | bool | False | Preserve isolated nodes in main graph |
| `--remove-singletons` | bool | False | Move isolated nodes to separate table |
| `--dry-run` | bool | False | Preview changes without applying them |
| `--show-progress` | bool | False | Display progress bars during operation |
| `--quiet` | bool | False | Suppress all output except errors |

#### Singleton Node Strategies

**Keep singletons** (default behavior):
- Isolated nodes remain in `nodes` table
- Only dangling edges are moved

**Remove singletons**:
- Isolated nodes moved to `singleton_nodes` table
- Main graph contains only connected nodes

#### Examples
```bash
# Basic pruning with singleton preservation
koza prune --database graph.duckdb --keep-singletons

# Remove singletons to separate table
koza prune --database graph.duckdb --remove-singletons

# Preview changes without applying
koza prune --database graph.duckdb --dry-run

# Quiet operation for automation
koza prune --database graph.duckdb --keep-singletons --quiet

# With progress tracking for large graphs
koza prune \
  --database large_graph.duckdb \
  --remove-singletons \
  --show-progress
```

#### Output
Creates additional tables for data preservation:
- **`dangling_edges`**: Edges pointing to non-existent nodes
- **`singleton_nodes`**: Isolated nodes (if `--remove-singletons`)
- **CLI summary**: Counts of edges/nodes moved, integrity statistics

---

### append

Add new KGX files to existing databases with schema evolution and optional deduplication.

#### Synopsis
```bash
koza append [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--database` | Path | Required | Existing DuckDB database to append to |
| `--nodes` | List[str] | None | Node files to append |
| `--edges` | List[str] | None | Edge files to append |
| `--deduplicate` | bool | False | Remove exact duplicates after appending |
| `--schema-report` | bool | False | Generate schema analysis after append |
| `--show-progress` | bool | False | Display progress bars during loading |
| `--quiet` | bool | False | Suppress all output except errors |

#### Schema Evolution

When appending files with new columns:
- New columns automatically added to existing tables
- Existing records get NULL values for new columns
- All schema changes are tracked and reported

#### Deduplication Strategy

When `--deduplicate` is enabled:
- Removes exact duplicates by ID field
- Keeps first occurrence of each duplicate ID
- Operates on both nodes and edges tables
- Reports number of duplicates removed

#### Examples
```bash
# Basic append operation
koza append \
  --database existing_graph.duckdb \
  --nodes new_genes.tsv \
  --edges new_interactions.jsonl

# Append with deduplication and schema reporting
koza append \
  --database graph.duckdb \
  --nodes genes_with_new_fields.tsv \
  --edges updated_interactions.parquet \
  --deduplicate \
  --schema-report

# Append multiple files with progress
koza append \
  --database graph.duckdb \
  --nodes "new_*.nodes.*" \
  --edges "new_*.edges.*" \
  --show-progress

# Quiet append for automation
koza append \
  --database graph.duckdb \
  --nodes corrections.tsv \
  --quiet
```

#### Output
- **Schema changes**: Reports new columns added and their sources
- **Record counts**: Shows before/after record counts for nodes and edges
- **Duplicate statistics**: Number of duplicates removed (if `--deduplicate`)
- **Schema report**: Detailed analysis (if `--schema-report`)

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

# Complex patterns
--nodes "**/genes*.{tsv,jsonl}"
```

#### Source Attribution
```bash
# Assign source names to files
--nodes "genes:genes.tsv" "proteins:proteins.jsonl"
--edges "interactions:interactions.parquet"
```

#### Mixed Specifications
```bash
# Combine different formats
--nodes genes.tsv "pathways:pathways.jsonl" proteins.parquet
```

### Progress and Logging

#### Progress Indicators
- `--show-progress`: Display progress bars for file operations
- `--quiet`: Suppress all non-error output
- Cannot use both flags together

#### Log Levels
Available for `transform` command:
- `DEBUG`: Verbose debugging information
- `INFO`: General information messages  
- `WARNING`: Warning messages (default)
- `ERROR`: Error messages only

### Output Formats

#### Supported Formats
- **TSV**: Tab-separated values (KGX standard)
- **JSONL**: JSON Lines format  
- **Parquet**: Columnar format for analytics

#### Format Selection
```bash
# Explicit format specification
--output-format tsv
--output-format jsonl  
--output-format parquet

# Automatic format detection from file extensions
# genes.tsv → TSV format
# genes.jsonl → JSONL format
# genes.parquet → Parquet format
```

## Error Handling

### Common Error Messages

#### File Not Found
```
Error: File not found: missing_file.tsv
```
**Solution**: Verify file paths and check file permissions

#### Database Not Found  
```
Error: Database not found: nonexistent.duckdb
```
**Solution**: Verify database path or create database with `join` command first

#### Schema Conflicts
```
Warning: Type conflict for column 'score' (INTEGER vs VARCHAR)
```
**Resolution**: DuckDB automatically resolves to most permissive type

#### Permission Issues
```
Error: Permission denied writing to output directory
```
**Solution**: Check write permissions on output directory

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (file not found, permission denied, etc.) |
| 2 | Invalid arguments or configuration |
| 130 | Interrupted by user (Ctrl+C) |

## Performance Tips

### For Large Files
1. **Use compressed formats** (`.gz`, `.bz2`) to reduce I/O
2. **Enable progress bars** to monitor long operations  
3. **Use Parquet format** for repeated analytical operations
4. **Process in chunks** using directory-based operations

### Memory Optimization
1. **Close other applications** during large operations
2. **Use streaming operations** (automatic for large files)
3. **Monitor disk space** for join operations
4. **Consider temporary directory** on fast storage

### Automation Scripts
1. **Use `--quiet` flag** to suppress output in scripts
2. **Check exit codes** for error handling
3. **Enable logging** for debugging automated workflows
4. **Use glob patterns** for flexible file matching

## Integration Examples

### Shell Scripts
```bash
#!/bin/bash
# Complete graph processing pipeline

set -e  # Exit on error

echo "Starting graph processing pipeline..."

# Join all source files
koza join \
  --nodes "sources/*.nodes.*" \
  --edges "sources/*.edges.*" \
  --output raw_graph.duckdb \
  --show-progress

# Clean up integrity issues
koza prune \
  --database raw_graph.duckdb \
  --keep-singletons

# Add corrected data
if [ -f "corrections.tsv" ]; then
  koza append \
    --database raw_graph.duckdb \
    --nodes corrections.tsv \
    --deduplicate \
    --quiet
fi

# Export by namespace
koza split \
  --database raw_graph.duckdb \
  --split-on namespace \
  --output-format parquet \
  --output-dir final_graphs

echo "Pipeline completed successfully"
```

### CI/CD Integration  
```yaml
# GitHub Actions example
name: Process Knowledge Graph
on: [push]

jobs:
  process-graph:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install Koza
        run: pip install koza
      - name: Join graph files
        run: |
          koza join \
            --input-dir ./data \
            --output graph.duckdb \
            --quiet
      - name: Clean graph
        run: |
          koza prune \
            --database graph.duckdb \
            --keep-singletons \
            --quiet
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: processed-graph
          path: graph.duckdb
```

### Configuration Files

While most commands use command-line arguments, complex configurations can be managed through:

1. **Environment variables** for commonly used paths
2. **Shell aliases** for frequently used command combinations  
3. **Configuration files** for transform operations (YAML format)
4. **Makefiles** for complex multi-step workflows

## Troubleshooting

### Getting Help
```bash
# General help
koza --help

# Command-specific help  
koza join --help
koza split --help
koza prune --help
koza append --help
koza transform --help
```

### Debug Information
```bash
# Enable verbose logging for transform
koza transform config.yaml --log-level DEBUG

# Use dry-run to preview prune operations
koza prune --database graph.duckdb --dry-run

# Generate schema reports for analysis
koza join --nodes "*.tsv" --schema-report
```

### Performance Monitoring
```bash
# Monitor large operations with progress
koza join --nodes "*.nodes.*" --edges "*.edges.*" --show-progress

# Time operations for benchmarking
time koza join --nodes "*.nodes.tsv" --quiet
```

For additional support, consult the [comprehensive graph operations guide](graph-operations.md) and the [Koza documentation](https://koza.monarchinitiative.org/).