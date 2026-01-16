# Reference

Technical reference documentation for graph operations. Use these pages to look up specific details about commands, APIs, and configuration options.

## Reference Sections

### [CLI Reference](cli.md)

Complete documentation for all graph operation CLI commands:

- `koza join` - Combine KGX files
- `koza split` - Split by field values
- `koza merge` - Complete pipeline
- `koza normalize` - Apply SSSOM mappings
- `koza deduplicate` - Remove duplicates
- `koza prune` - Clean graph integrity
- `koza append` - Add to existing database
- `koza report` - Generate reports
- `koza node-report` / `koza edge-report` - Tabular reports
- `koza node-examples` / `koza edge-examples` - Sample extraction

Each command includes:

- Synopsis and description
- All options with types and defaults
- Usage examples
- Output description

### [Python API](api.md)

Auto-generated documentation from source code docstrings:

- `join_graphs()` - Join operation
- `split_graph()` - Split operation
- `merge_graphs()` - Pipeline orchestration
- `normalize_graph()` - SSSOM normalization
- `deduplicate_graph()` - Deduplication
- `prune_graph()` - Graph cleaning
- `append_graphs()` - Incremental updates
- Report generation functions

### [Configuration](configuration.md)

Detailed documentation for all configuration models:

- `FileSpec` - File specification with format detection
- `JoinConfig` - Join operation settings
- `SplitConfig` - Split operation settings
- `MergeConfig` - Pipeline configuration
- `NormalizeConfig` - Normalization settings
- `DeduplicateConfig` - Deduplication settings
- `PruneConfig` - Pruning settings
- `AppendConfig` - Append settings
- Report configuration models

Each model includes:

- All fields with types
- Default values
- Validation rules
- Usage examples

## File Formats

### Supported Input Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| TSV | `.tsv` | Tab-separated values (KGX standard) |
| JSONL | `.jsonl` | JSON Lines (one record per line) |
| Parquet | `.parquet` | Columnar format (efficient for large files) |

Compression supported: `.gz`, `.bz2`, `.xz`

### KGX File Types

| Type | Required Columns | Optional Columns |
|------|-----------------|------------------|
| Nodes | `id` | `category`, `name`, `provided_by`, ... |
| Edges | `subject`, `predicate`, `object` | `id`, `category`, `provided_by`, ... |
