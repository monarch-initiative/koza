# Configuration Reference

This reference documents all Pydantic configuration models used in Koza graph operations.

---

## Enums

### KGXFormat

Supported KGX file formats.

| Value | Description |
|-------|-------------|
| `TSV` | Tab-separated values format |
| `JSONL` | JSON Lines format |
| `PARQUET` | Apache Parquet format |

### KGXFileType

KGX file types.

| Value | Description |
|-------|-------------|
| `NODES` | Node file |
| `EDGES` | Edge file |

### TabularReportFormat

Supported formats for tabular reports.

| Value | Description |
|-------|-------------|
| `TSV` | Tab-separated values format |
| `JSONL` | JSON Lines format |
| `PARQUET` | Apache Parquet format |

---

## File Handling

### FileSpec

Specification for a KGX file with automatic format detection and source attribution.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `path` | `Path` | **required** | Path to the file |
| `source_name` | `str \| None` | file stem | Source attribution name (defaults to filename stem) |
| `format` | `KGXFormat \| None` | auto-detect | File format (TSV, JSONL, PARQUET) |
| `file_type` | `KGXFileType \| None` | auto-detect | File type (NODES, EDGES) |

#### Validation Rules

- **Format Detection**: If `format` is not provided, it is auto-detected from the file extension:
    - `.tsv`, `.txt` -> `TSV`
    - `.jsonl`, `.json` -> `JSONL`
    - `.parquet` -> `PARQUET`
    - Compressed files (`.gz`, `.bz2`, `.xz`) are handled by stripping the compression suffix first
- **File Type Detection**: If `file_type` is not provided, it is auto-detected from the filename:
    - Files containing `_nodes.` or starting with `nodes.` -> `NODES`
    - Files containing `_edges.` or starting with `edges.` -> `EDGES`
- **Source Name**: If not provided, defaults to the stem of the file path

#### Example

```python
from koza.model.graph_operations import FileSpec

# Full specification
file_spec = FileSpec(
    path=Path("data/monarch_nodes.tsv"),
    source_name="monarch",
    format=KGXFormat.TSV,
    file_type=KGXFileType.NODES
)

# With auto-detection (recommended)
file_spec = FileSpec(path=Path("data/monarch_nodes.tsv"))
# Automatically detects: format=TSV, file_type=NODES, source_name="monarch_nodes"
```

---

## Operation Configurations

### JoinConfig

Configuration for the join operation, which loads multiple KGX files into a unified database.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `node_files` | `list[FileSpec]` | `[]` | List of node files to join |
| `edge_files` | `list[FileSpec]` | `[]` | List of edge files to join |
| `output_database` | `Path \| None` | `None` | Path for output DuckDB database |
| `schema_reporting` | `bool` | `True` | Enable schema analysis reporting |
| `preserve_duplicates` | `bool` | `False` | Keep duplicate records during join |
| `generate_provided_by` | `bool` | `True` | Add `provided_by` column from filename |
| `database_path` | `Path \| None` | `None` | Database path (inherited from base) |
| `output_format` | `KGXFormat` | `TSV` | Output format for exports |
| `quiet` | `bool` | `False` | Suppress progress output |
| `show_progress` | `bool` | `True` | Show progress indicators |

#### Validation Rules

- If `output_database` is provided, it automatically sets `database_path` for compatibility

#### Example

```python
from koza.model.graph_operations import JoinConfig, FileSpec

config = JoinConfig(
    node_files=[
        FileSpec(path=Path("data/source1_nodes.tsv")),
        FileSpec(path=Path("data/source2_nodes.tsv")),
    ],
    edge_files=[
        FileSpec(path=Path("data/source1_edges.tsv")),
        FileSpec(path=Path("data/source2_edges.tsv")),
    ],
    output_database=Path("merged.duckdb"),
    generate_provided_by=True
)
```

---

### JoinResult

Result of the join operation.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `files_loaded` | `list[FileLoadResult]` | **required** | Details for each loaded file |
| `final_stats` | `DatabaseStats` | **required** | Final database statistics |
| `schema_report` | `dict[str, Any] \| None` | `None` | Schema analysis report |
| `total_time_seconds` | `float` | **required** | Total operation time |
| `database_path` | `Path \| None` | `None` | Path to the created database |

---

### SplitConfig

Configuration for the split operation, which splits a KGX file based on field values.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `input_file` | `FileSpec` | **required** | Input file to split |
| `split_fields` | `list[str]` | **required** | Fields to split on |
| `output_directory` | `Path` | `./output` | Directory for output files |
| `remove_prefixes` | `bool` | `False` | Remove prefixes from split values |
| `output_format` | `KGXFormat \| None` | `None` | Output format (None = preserve original) |
| `database_path` | `Path \| None` | `None` | Database path (inherited from base) |
| `quiet` | `bool` | `False` | Suppress progress output |
| `show_progress` | `bool` | `True` | Show progress indicators |

#### Example

```python
from koza.model.graph_operations import SplitConfig, FileSpec

config = SplitConfig(
    input_file=FileSpec(path=Path("data/all_nodes.tsv")),
    split_fields=["category", "provided_by"],
    output_directory=Path("split_output"),
    remove_prefixes=True
)
```

---

### SplitResult

Result of the split operation.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `input_file` | `FileSpec` | **required** | The input file that was split |
| `output_files` | `list[Path]` | **required** | Paths to created output files |
| `total_records_split` | `int` | **required** | Total records processed |
| `split_values` | `list[dict[str, str]]` | **required** | Unique value combinations found |
| `total_time_seconds` | `float` | **required** | Total operation time |

---

### MergeConfig

Configuration for the merge operation, which is a composite pipeline combining join, deduplicate, normalize, and prune operations.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| **Input Files** | | | |
| `node_files` | `list[FileSpec]` | `[]` | List of node files to merge |
| `edge_files` | `list[FileSpec]` | `[]` | List of edge files to merge |
| `mapping_files` | `list[FileSpec]` | `[]` | SSSOM mapping files for normalization |
| **Pipeline Options** | | | |
| `skip_deduplicate` | `bool` | `False` | Skip deduplication step |
| `skip_normalize` | `bool` | `False` | Skip normalization step |
| `skip_prune` | `bool` | `False` | Skip pruning step |
| `generate_provided_by` | `bool` | `True` | Add `provided_by` column from filename |
| `continue_on_pipeline_step_error` | `bool` | `True` | Continue on non-critical errors |
| **Prune Options** | | | |
| `keep_singletons` | `bool` | `True` | Preserve isolated nodes |
| `remove_singletons` | `bool` | `False` | Move singletons to separate table |
| **Output Options** | | | |
| `output_database` | `Path \| None` | `None` | Path for output database (None = temporary) |
| `output_format` | `KGXFormat` | `TSV` | Format for exported files |
| `export_final` | `bool` | `False` | Export final clean data to files |
| `export_directory` | `Path \| None` | `None` | Directory for exported files |
| `archive` | `bool` | `False` | Export as archive instead of loose files |
| `compress` | `bool` | `False` | Compress archive as tar.gz |
| `graph_name` | `str \| None` | `None` | Name for graph files in archive |
| **General Options** | | | |
| `quiet` | `bool` | `False` | Suppress progress output |
| `show_progress` | `bool` | `True` | Show progress indicators |
| `schema_reporting` | `bool` | `True` | Enable schema analysis reporting |

#### Validation Rules

- **Files Required**: At least one node or edge file must be provided
- **Normalize Requirements**: If `skip_normalize` is `False`, mapping files must be provided
- **Singleton Options**: Cannot set both `keep_singletons` and `remove_singletons` to `True`
- **Export Requirements**: If `export_final` is `True`, `export_directory` must be provided
- **Archive Requirements**: `compress` requires `archive` to be enabled

#### Example

```python
from koza.model.graph_operations import MergeConfig, FileSpec

config = MergeConfig(
    node_files=[
        FileSpec(path=Path("data/source1_nodes.tsv")),
        FileSpec(path=Path("data/source2_nodes.tsv")),
    ],
    edge_files=[
        FileSpec(path=Path("data/source1_edges.tsv")),
        FileSpec(path=Path("data/source2_edges.tsv")),
    ],
    mapping_files=[
        FileSpec(path=Path("mappings/disease_mappings.sssom.tsv")),
    ],
    output_database=Path("merged.duckdb"),
    export_final=True,
    export_directory=Path("output"),
    archive=True,
    compress=True,
    graph_name="my-knowledge-graph"
)
```

---

### MergeResult

Result of the merge operation.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `success` | `bool` | **required** | Whether the operation succeeded |
| `join_result` | `JoinResult \| None` | `None` | Result from join step |
| `deduplicate_result` | `DeduplicateResult \| None` | `None` | Result from deduplicate step |
| `normalize_result` | `NormalizeResult \| None` | `None` | Result from normalize step |
| `prune_result` | `PruneResult \| None` | `None` | Result from prune step |
| `operations_completed` | `list[str]` | `[]` | Names of completed operations |
| `operations_skipped` | `list[str]` | `[]` | Names of skipped operations |
| `final_stats` | `DatabaseStats \| None` | `None` | Final database statistics |
| `database_path` | `Path \| None` | `None` | Path to the database |
| `exported_files` | `list[Path]` | `[]` | Paths to exported files |
| `total_time_seconds` | `float` | **required** | Total operation time |
| `summary` | `OperationSummary` | **required** | Summary for CLI output |
| `errors` | `list[str]` | `[]` | Error messages |
| `warnings` | `list[str]` | `[]` | Warning messages |

---

### NormalizeConfig

Configuration for the normalize operation, which applies SSSOM mappings to normalize identifiers in edges.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `database_path` | `Path` | **required** | Path to the DuckDB database |
| `mapping_files` | `list[FileSpec]` | `[]` | SSSOM mapping files |
| `quiet` | `bool` | `False` | Suppress progress output |
| `show_progress` | `bool` | `True` | Show progress indicators |

#### Validation Rules

- **Database Exists**: The database file must exist
- **Mapping Files Required**: At least one SSSOM mapping file must be provided

#### Example

```python
from koza.model.graph_operations import NormalizeConfig, FileSpec

config = NormalizeConfig(
    database_path=Path("merged.duckdb"),
    mapping_files=[
        FileSpec(path=Path("mappings/disease_mappings.sssom.tsv")),
        FileSpec(path=Path("mappings/gene_mappings.sssom.tsv")),
    ]
)
```

---

### NormalizeResult

Result of the normalize operation.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `success` | `bool` | **required** | Whether the operation succeeded |
| `mappings_loaded` | `list[FileLoadResult]` | **required** | Details for each loaded mapping file |
| `edges_normalized` | `int` | **required** | Number of edges normalized |
| `final_stats` | `DatabaseStats \| None` | `None` | Final database statistics |
| `total_time_seconds` | `float` | **required** | Total operation time |
| `summary` | `OperationSummary` | **required** | Summary for CLI output |
| `errors` | `list[str]` | `[]` | Error messages |
| `warnings` | `list[str]` | `[]` | Warning messages |

---

### DeduplicateConfig

Configuration for the deduplicate operation, which removes duplicate nodes and edges.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `database_path` | `Path` | **required** | Path to the DuckDB database |
| `deduplicate_nodes` | `bool` | `True` | Deduplicate nodes table |
| `deduplicate_edges` | `bool` | `True` | Deduplicate edges table |
| `quiet` | `bool` | `False` | Suppress progress output |
| `show_progress` | `bool` | `True` | Show progress indicators |

#### Validation Rules

- **Database Exists**: The database file must exist

#### Example

```python
from koza.model.graph_operations import DeduplicateConfig

config = DeduplicateConfig(
    database_path=Path("merged.duckdb"),
    deduplicate_nodes=True,
    deduplicate_edges=True
)
```

---

### DeduplicateResult

Result of the deduplicate operation.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `success` | `bool` | **required** | Whether the operation succeeded |
| `duplicate_nodes_found` | `int` | `0` | Number of duplicate nodes found |
| `duplicate_nodes_removed` | `int` | `0` | Rows removed from nodes table |
| `duplicate_edges_found` | `int` | `0` | Number of duplicate edges found |
| `duplicate_edges_removed` | `int` | `0` | Rows removed from edges table |
| `final_stats` | `DatabaseStats \| None` | `None` | Final database statistics |
| `total_time_seconds` | `float` | **required** | Total operation time |
| `summary` | `OperationSummary` | **required** | Summary for CLI output |
| `errors` | `list[str]` | `[]` | Error messages |
| `warnings` | `list[str]` | `[]` | Warning messages |

---

### PruneConfig

Configuration for the prune operation, which handles dangling edges and singleton nodes.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `database_path` | `Path` | **required** | Path to the DuckDB database |
| `keep_singletons` | `bool` | `True` | Preserve isolated nodes |
| `remove_singletons` | `bool` | `False` | Move singletons to separate table |
| `min_component_size` | `int \| None` | `None` | Minimum connected component size |
| `quiet` | `bool` | `False` | Suppress progress output |
| `show_progress` | `bool` | `True` | Show progress indicators |
| `output_format` | `KGXFormat \| None` | `None` | Format for any exported files |

#### Validation Rules

- **Database Exists**: The database file must exist
- **Singleton Options**: Cannot set both `keep_singletons` and `remove_singletons` to `True`

#### Example

```python
from koza.model.graph_operations import PruneConfig

config = PruneConfig(
    database_path=Path("merged.duckdb"),
    keep_singletons=False,
    remove_singletons=True
)
```

---

### PruneResult

Result of the prune operation.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `database_path` | `Path` | **required** | Path to the database |
| `dangling_edges_moved` | `int` | **required** | Number of dangling edges moved |
| `singleton_nodes_moved` | `int` | **required** | Number of singleton nodes moved |
| `singleton_nodes_kept` | `int` | **required** | Number of singleton nodes kept |
| `final_stats` | `DatabaseStats` | **required** | Final database statistics |
| `dangling_edges_by_source` | `dict[str, int]` | `{}` | Dangling edges grouped by source |
| `missing_nodes_by_source` | `dict[str, int]` | `{}` | Missing nodes grouped by source |
| `total_time_seconds` | `float` | **required** | Total operation time |
| `success` | `bool` | **required** | Whether the operation succeeded |
| `errors` | `list[str]` | `[]` | Error messages |

---

### AppendConfig

Configuration for the append operation, which adds new files to an existing database.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `database_path` | `Path` | **required** | Path to the existing DuckDB database |
| `node_files` | `list[FileSpec]` | `[]` | Node files to append |
| `edge_files` | `list[FileSpec]` | `[]` | Edge files to append |
| `deduplicate` | `bool` | `False` | Run deduplication after append |
| `quiet` | `bool` | `False` | Suppress progress output |
| `show_progress` | `bool` | `True` | Show progress indicators |
| `schema_reporting` | `bool` | `False` | Enable schema analysis reporting |

#### Validation Rules

- **Database Exists**: The database file must exist
- **Files Required**: At least one node or edge file must be provided

#### Example

```python
from koza.model.graph_operations import AppendConfig, FileSpec

config = AppendConfig(
    database_path=Path("merged.duckdb"),
    node_files=[
        FileSpec(path=Path("data/new_nodes.tsv")),
    ],
    edge_files=[
        FileSpec(path=Path("data/new_edges.tsv")),
    ],
    deduplicate=True
)
```

---

### AppendResult

Result of the append operation.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `database_path` | `Path` | **required** | Path to the database |
| `files_loaded` | `list[FileLoadResult]` | **required** | Details for each loaded file |
| `records_added` | `int` | **required** | Number of records added |
| `new_columns_added` | `int` | **required** | Number of new columns added |
| `schema_changes` | `list[str]` | `[]` | Description of schema changes |
| `final_stats` | `DatabaseStats` | **required** | Final database statistics |
| `schema_report` | `dict[str, Any] \| None` | `None` | Schema analysis report |
| `duplicates_handled` | `int` | `0` | Number of duplicates handled |
| `total_time_seconds` | `float` | **required** | Total operation time |

---

## Report Configurations

### QCReportConfig

Configuration for QC (Quality Control) report generation.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `database_path` | `Path` | **required** | Path to the DuckDB database |
| `output_file` | `Path \| None` | `None` | Path for output YAML file |
| `group_by` | `str` | `"provided_by"` | Column to group statistics by |
| `quiet` | `bool` | `False` | Suppress progress output |

#### Example

```python
from koza.model.graph_operations import QCReportConfig

config = QCReportConfig(
    database_path=Path("merged.duckdb"),
    output_file=Path("qc_report.yaml"),
    group_by="provided_by"
)
```

---

### GraphStatsConfig

Configuration for graph statistics report generation.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `database_path` | `Path` | **required** | Path to the DuckDB database |
| `output_file` | `Path \| None` | `None` | Path for output YAML file |
| `quiet` | `bool` | `False` | Suppress progress output |

#### Example

```python
from koza.model.graph_operations import GraphStatsConfig

config = GraphStatsConfig(
    database_path=Path("merged.duckdb"),
    output_file=Path("graph_stats.yaml")
)
```

---

### SchemaReportConfig

Configuration for schema analysis report generation.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `database_path` | `Path` | **required** | Path to the DuckDB database |
| `output_file` | `Path \| None` | `None` | Path for output YAML file |
| `include_biolink_compliance` | `bool` | `True` | Include Biolink model compliance analysis |
| `quiet` | `bool` | `False` | Suppress progress output |

#### Example

```python
from koza.model.graph_operations import SchemaReportConfig

config = SchemaReportConfig(
    database_path=Path("merged.duckdb"),
    output_file=Path("schema_report.yaml"),
    include_biolink_compliance=True
)
```

---

### NodeReportConfig

Configuration for tabular node report generation.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `database_path` | `Path \| None` | `None` | Path to the DuckDB database |
| `node_file` | `FileSpec \| None` | `None` | Node file to load (alternative to database) |
| `output_file` | `Path \| None` | `None` | Path for output file |
| `output_format` | `TabularReportFormat` | `TSV` | Output format |
| `categorical_columns` | `list[str]` | `["namespace", "category", "in_taxon", "provided_by"]` | Columns to group by |
| `quiet` | `bool` | `False` | Suppress progress output |

#### Validation Rules

- **Input Required**: Either `database_path` or `node_file` must be provided

#### Example

```python
from koza.model.graph_operations import NodeReportConfig

config = NodeReportConfig(
    database_path=Path("merged.duckdb"),
    output_file=Path("node_report.tsv"),
    categorical_columns=["category", "provided_by"]
)
```

---

### EdgeReportConfig

Configuration for tabular edge report generation.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `database_path` | `Path \| None` | `None` | Path to the DuckDB database |
| `node_file` | `FileSpec \| None` | `None` | Node file to load (for category enrichment) |
| `edge_file` | `FileSpec \| None` | `None` | Edge file to load (alternative to database) |
| `output_file` | `Path \| None` | `None` | Path for output file |
| `output_format` | `TabularReportFormat` | `TSV` | Output format |
| `categorical_columns` | `list[str]` | see below | Columns to group by |
| `quiet` | `bool` | `False` | Suppress progress output |

**Default categorical columns:**

- `subject_category`
- `subject_namespace`
- `predicate`
- `object_category`
- `object_namespace`
- `primary_knowledge_source`
- `aggregator_knowledge_source`
- `knowledge_level`
- `agent_type`
- `provided_by`

#### Validation Rules

- **Input Required**: Either `database_path` or `edge_file` must be provided

#### Example

```python
from koza.model.graph_operations import EdgeReportConfig

config = EdgeReportConfig(
    database_path=Path("merged.duckdb"),
    output_file=Path("edge_report.tsv"),
    categorical_columns=["predicate", "subject_category", "object_category"]
)
```

---

### NodeExamplesConfig

Configuration for node examples generation.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `database_path` | `Path \| None` | `None` | Path to the DuckDB database |
| `node_file` | `FileSpec \| None` | `None` | Node file to load (alternative to database) |
| `output_file` | `Path \| None` | `None` | Path for output file |
| `output_format` | `TabularReportFormat` | `TSV` | Output format |
| `sample_size` | `int` | `5` | Number of examples per type |
| `type_column` | `str` | `"category"` | Column defining the type for grouping |
| `quiet` | `bool` | `False` | Suppress progress output |

#### Validation Rules

- **Input Required**: Either `database_path` or `node_file` must be provided

#### Example

```python
from koza.model.graph_operations import NodeExamplesConfig

config = NodeExamplesConfig(
    database_path=Path("merged.duckdb"),
    output_file=Path("node_examples.tsv"),
    sample_size=10,
    type_column="category"
)
```

---

### EdgeExamplesConfig

Configuration for edge examples generation.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `database_path` | `Path \| None` | `None` | Path to the DuckDB database |
| `node_file` | `FileSpec \| None` | `None` | Node file to load (for category enrichment) |
| `edge_file` | `FileSpec \| None` | `None` | Edge file to load (alternative to database) |
| `output_file` | `Path \| None` | `None` | Path for output file |
| `output_format` | `TabularReportFormat` | `TSV` | Output format |
| `sample_size` | `int` | `5` | Number of examples per type |
| `type_columns` | `list[str]` | `["subject_category", "predicate", "object_category"]` | Columns defining the type for grouping |
| `quiet` | `bool` | `False` | Suppress progress output |

#### Validation Rules

- **Input Required**: Either `database_path` or `edge_file` must be provided

#### Example

```python
from koza.model.graph_operations import EdgeExamplesConfig

config = EdgeExamplesConfig(
    database_path=Path("merged.duckdb"),
    output_file=Path("edge_examples.tsv"),
    sample_size=10,
    type_columns=["predicate", "primary_knowledge_source"]
)
```

---

## Supporting Models

### DatabaseStats

Database statistics model used in operation results.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `nodes` | `int` | `0` | Total node count |
| `edges` | `int` | `0` | Total edge count |
| `dangling_edges` | `int` | `0` | Edges with missing subject/object nodes |
| `duplicate_nodes` | `int` | `0` | Duplicate node count |
| `singleton_nodes` | `int` | `0` | Nodes with no edges |
| `database_size_mb` | `float \| None` | `None` | Database size in megabytes |

---

### FileLoadResult

Result of loading a single file.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `file_spec` | `FileSpec` | **required** | The file specification |
| `records_loaded` | `int` | **required** | Number of records loaded |
| `detected_format` | `KGXFormat` | **required** | Detected file format |
| `load_time_seconds` | `float` | **required** | Time to load the file |
| `errors` | `list[str]` | `[]` | Any errors during loading |
| `temp_table_name` | `str \| None` | `None` | Temp table name for schema analysis |

---

### OperationSummary

Summary statistics for CLI output.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `operation` | `str` | **required** | Operation name |
| `success` | `bool` | **required** | Whether operation succeeded |
| `message` | `str` | **required** | Summary message |
| `stats` | `DatabaseStats \| None` | `None` | Database statistics |
| `files_processed` | `int` | `0` | Number of files processed |
| `total_time_seconds` | `float` | `0.0` | Total operation time |
| `warnings` | `list[str]` | `[]` | Warning messages |
| `errors` | `list[str]` | `[]` | Error messages |
