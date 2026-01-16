# Configuration Reference

!!! note "Coming Soon"
    This reference is under development.

Detailed documentation for all configuration models.

## File Specification

### FileSpec

Specifies an input file with format detection and source attribution.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `path` | `Path` | required | Path to the file |
| `source_name` | `str` | file stem | Source attribution name |
| `format` | `KGXFormat` | auto-detect | File format (TSV, JSONL, PARQUET) |
| `file_type` | `KGXFileType` | auto-detect | File type (NODES, EDGES) |

## Operation Configs

*Detailed configuration documentation coming soon...*

### JoinConfig
### SplitConfig
### MergeConfig
### NormalizeConfig
### DeduplicateConfig
### PruneConfig
### AppendConfig

## Report Configs

### QCReportConfig
### GraphStatsConfig
### SchemaReportConfig
### NodeReportConfig
### EdgeReportConfig
