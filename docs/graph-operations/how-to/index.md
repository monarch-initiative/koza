# How-to Guides

Step-by-step instructions for specific graph operation tasks. Each guide focuses on a single goal.

## Data Loading & Combination

### [Join Files](join-files.md)
Combine multiple KGX files into a unified database. Covers basic joins, mixed formats, glob patterns, and schema reporting.

### [Incremental Updates](incremental-updates.md)
Add new data to an existing database, with options for schema updates and deduplication.

## Data Transformation

### [Split Graphs](split-graph.md)
Divide a graph into subsets based on field values such as source, category, or other attributes.

### [Normalize IDs](normalize-ids.md)
Apply SSSOM mappings to harmonize identifiers across different naming conventions and ontologies.

### [Clean Graphs](clean-graph.md)
Remove duplicates, dangling edges, and optionally singleton nodes from a graph.

## Reporting & Analysis

### [Generate Reports](generate-reports.md)
Create QC reports, graph statistics, schema compliance reports, and tabular summaries.

### [Export Formats](export-formats.md)
Export your graph to TSV, JSONL, or Parquet format, with optional archiving and compression.

## Guide Format

Each how-to guide follows a consistent structure:

1. **Goal**: What you'll accomplish
2. **Prerequisites**: What you need before starting
3. **Steps**: Numbered instructions with examples
4. **Verification**: How to confirm success
5. **Variations**: Alternative approaches and options

## Quick Reference

| Task | Command | Guide |
|------|---------|-------|
| Combine files | `koza join` | [Join Files](join-files.md) |
| Add to existing | `koza append` | [Incremental Updates](incremental-updates.md) |
| Extract subset | `koza split` | [Split Graphs](split-graph.md) |
| Harmonize IDs | `koza normalize` | [Normalize IDs](normalize-ids.md) |
| Remove issues | `koza prune` / `koza deduplicate` | [Clean Graphs](clean-graph.md) |
| Quality reports | `koza report` | [Generate Reports](generate-reports.md) |
| Format conversion | `koza split --format` | [Export Formats](export-formats.md) |
