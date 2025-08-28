# Koza Configuration (KozaConfig)

This document describes the KozaConfig model introduced in Koza 2, which replaces the previous SourceConfig structure. The KozaConfig provides a comprehensive configuration system for data ingests with support for multiple readers, transforms, and writers.

!!! tip "Paths are relative to the directory from which you execute Koza."

## Overview

KozaConfig is the main configuration class that defines how Koza processes your data. It consists of several main sections:

- **name**: Unique identifier for your ingest
- **reader/readers**: Configuration for input data sources  
- **transform**: Configuration for data transformation logic
- **writer**: Configuration for output format and properties
- **metadata**: Optional metadata about the dataset

## Basic Structure

```yaml
name: 'my-ingest'
reader: # OR readers: for multiple sources
  # reader configuration
transform:
  # transformation configuration  
writer:
  # output configuration
metadata: # optional
  # metadata configuration
```

## Core Configuration Properties

### Required Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | string | Name of the data ingest, should be unique and descriptive |

### Optional Properties

| Property | Type | Description |
|----------|------|-------------|
| `reader` | ReaderConfig | Single reader configuration (mutually exclusive with `readers`) |
| `readers` | dict[str, ReaderConfig] | Named multiple readers (mutually exclusive with `reader`) |
| `transform` | TransformConfig | Transform configuration (optional, uses defaults if not specified) |
| `writer` | WriterConfig | Writer configuration (optional, uses defaults if not specified) |
| `metadata` | DatasetDescription \| string | Dataset metadata or path to metadata file |

## Reader Configuration

Readers define how Koza processes input data files. You can use either a single `reader` or multiple named `readers`.

### Single Reader Example
```yaml
reader:
  format: csv
  files:
    - 'data/input.tsv'
  delimiter: '\t'
```

### Multiple Readers Example  
```yaml
readers:
  main_data:
    format: csv
    files:
      - 'data/main.tsv'
    delimiter: '\t'
  reference_data:
    format: json
    files:
      - 'data/reference.json'
```

### Base Reader Properties

All reader types support these common properties:

| Property | Type | Description |
|----------|------|-------------|
| `files` | list[string] | List of input files to process |
| `filters` | list[ColumnFilter] | List of filters to apply to data |

### CSV Reader Configuration

For CSV format files (`format: csv`):

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `format` | string | `csv` | Must be "csv" |
| `columns` | list[string \| dict] | None | Column names or name/type mappings |
| `field_type_map` | dict[string, FieldType] | None | Mapping of column names to types |
| `delimiter` | string | `\t` | Field delimiter (supports "tab", "\\t", or literal chars) |
| `header_delimiter` | string | None | Different delimiter for header row |
| `dialect` | string | `excel` | CSV dialect |
| `header_mode` | int \| HeaderMode | `infer` | Header handling: int (0-based row), "infer", or "none" |
| `header_prefix` | string | None | Prefix for header processing |
| `skip_blank_lines` | bool | `true` | Whether to skip blank lines |
| `comment_char` | string | `#` | Character that indicates comments |

#### Field Types
- `str` - String type (default)
- `int` - Integer type  
- `float` - Float type

#### Header Modes
- `infer` - Automatically detect header row
- `none` - No header row present
- Integer (0-based) - Specific header row index

#### Column Definition Examples
```yaml
# Simple string columns
columns:
  - 'gene_id'
  - 'symbol'
  - 'score'

# Mixed types  
columns:
  - 'gene_id'
  - 'symbol' 
  - 'score': 'int'
  - 'p_value': 'float'
```

### JSON Reader Configuration  

For JSON format files (`format: json`):

| Property | Type | Description |
|----------|------|-------------|
| `format` | string | Must be "json" |
| `required_properties` | list[string] | Properties that must be present |
| `json_path` | list[string \| int] | Path to data within JSON structure |

### JSONL Reader Configuration

For JSON Lines format files (`format: jsonl`):

| Property | Type | Description |
|----------|------|-------------|
| `format` | string | Must be "jsonl" |
| `required_properties` | list[string] | Properties that must be present |

### YAML Reader Configuration

For YAML format files (`format: yaml`):

| Property | Type | Description |
|----------|------|-------------|
| `format` | string | Must be "yaml" |
| `required_properties` | list[string] | Properties that must be present |
| `json_path` | list[string \| int] | Path to data within YAML structure |

## Column Filters

Filters allow you to include or exclude rows based on column values.

### Filter Types

#### Comparison Filters
For numeric comparisons:

```yaml
filters:
  - inclusion: 'include'  # or 'exclude'
    column: 'score'
    filter_code: 'gt'     # gt, ge, lt, le  
    value: 500
```

#### Equality Filters  
For exact matches:

```yaml
filters:
  - inclusion: 'include'
    column: 'status'
    filter_code: 'eq'     # eq, ne
    value: 'active'
```

#### List Filters
For checking membership in lists:

```yaml
filters:
  - inclusion: 'include'
    column: 'category'
    filter_code: 'in'     # in, in_exact
    value: ['A', 'B', 'C']
```

### Filter Codes
- `gt` - Greater than
- `ge` - Greater than or equal  
- `lt` - Less than
- `le` - Less than or equal
- `eq` - Equal to
- `ne` - Not equal to
- `in` - In list (case insensitive)
- `in_exact` - In list (exact match)

## Transform Configuration

The transform section configures how data is processed and transformed.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `code` | string | None | Path to Python transform file |
| `module` | string | None | Python module to import |
| `global_table` | string \| dict | None | Global translation table |
| `local_table` | string \| dict | None | Local translation table |
| `mappings` | list[string] | `[]` | List of mapping files |
| `on_map_failure` | MapErrorEnum | `warning` | How to handle mapping failures |
| `extra_fields` | dict | `{}` | Additional custom fields |

### Map Error Handling
- `warning` - Log warnings for mapping failures
- `error` - Raise errors for mapping failures

### Example Transform Configuration
```yaml
transform:
  code: 'transform.py'
  global_table: 'tables/global_mappings.yaml'
  local_table: 'tables/local_mappings.yaml'
  mappings:
    - 'mappings/gene_mappings.yaml'
  on_map_failure: 'warning'
  custom_param: 'value'  # Goes into extra_fields
```

## Writer Configuration

The writer section configures output format and properties.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `format` | OutputFormat | `tsv` | Output format |
| `sssom_config` | SSSOMConfig | None | SSSOM mapping configuration |
| `node_properties` | list[string] | None | Node properties to include |
| `edge_properties` | list[string] | None | Edge properties to include |
| `min_node_count` | int | None | Minimum nodes required |
| `min_edge_count` | int | None | Minimum edges required |

### Output Formats
- `tsv` - Tab-separated values
- `jsonl` - JSON Lines  
- `kgx` - KGX format
- `passthrough` - Pass data through unchanged

### Example Writer Configuration
```yaml
writer:
  format: tsv
  node_properties:
    - 'id'
    - 'category'
    - 'name'
  edge_properties:
    - 'id'
    - 'subject'
    - 'predicate'
    - 'object'
    - 'category'
```

### SSSOM Configuration

SSSOM (Simple Standard for Sharing Ontological Mappings) integration:

| Property | Type | Description |
|----------|------|-------------|
| `files` | list[string] | SSSOM mapping files |
| `filter_prefixes` | list[string] | Prefixes to filter by |
| `subject_target_prefixes` | list[string] | Subject mapping prefixes |
| `object_target_prefixes` | list[string] | Object mapping prefixes |
| `use_match` | list[Match] | Match types to use |

#### Match Types
- `exact` - Exact matches
- `narrow` - Narrow matches  
- `broad` - Broad matches

```yaml
writer:
  sssom_config:
    files:
      - 'mappings/ontology_mappings.sssom.tsv'
    subject_target_prefixes: ['MONDO']
    object_target_prefixes: ['HP', 'GO']
    use_match: ['exact']
```

## Metadata Configuration

Metadata can be defined inline or loaded from a separate file.

### Inline Metadata
```yaml
metadata:
  name: 'My Data Source'
  description: 'Description of the data and processing'
  ingest_title: 'Source Database Name'
  ingest_url: 'https://source-database.org'
  provided_by: 'my_source_gene_disease'
  rights: 'https://source-database.org/license'
```

### External Metadata File
```yaml
metadata: './metadata.yaml'
```

### Metadata Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | string | Human-readable name of data source |
| `ingest_title` | string | Title of data source (maps to biolink name) |
| `ingest_url` | string | URL of data source (maps to biolink iri) |
| `description` | string | Description of data/ingest process |
| `provided_by` | string | Source identifier, format: `<source>_<type>` |
| `rights` | string | License/rights information URL |

## Complete Example

Here's a comprehensive example showing all major configuration options:

```yaml
name: 'comprehensive-example'

metadata:
  name: 'Example Database'
  description: 'Comprehensive example of Koza configuration'
  ingest_title: 'Example DB'
  ingest_url: 'https://example-db.org'
  provided_by: 'example_gene_disease'
  rights: 'https://example-db.org/license'

reader:
  format: csv
  files:
    - 'data/genes.tsv'
    - 'data/diseases.tsv'
  delimiter: '\t'
  columns:
    - 'gene_id'
    - 'gene_symbol'
    - 'disease_id'
    - 'confidence': 'float'
  filters:
    - inclusion: 'include'
      column: 'confidence'
      filter_code: 'ge'
      value: 0.7
    - inclusion: 'exclude'
      column: 'gene_symbol'
      filter_code: 'eq'
      value: 'DEPRECATED'

transform:
  code: 'transform.py'
  global_table: 'tables/global_mappings.yaml'
  on_map_failure: 'warning'

writer:
  format: tsv
  node_properties:
    - 'id'
    - 'category'
    - 'name'
    - 'provided_by'
  edge_properties:
    - 'id'
    - 'subject'
    - 'predicate'
    - 'object'
    - 'category'
    - 'provided_by'
    - 'confidence'
  min_node_count: 100
  min_edge_count: 50
```

## Migration from SourceConfig

If you're migrating from the old SourceConfig format to KozaConfig:

1. **Structure Changes**: 
   - Top-level properties are now organized under `reader`, `transform`, and `writer` sections
   - `files` moves to `reader.files`
   - Transform-related properties move to `transform` section
   - Output properties move to `writer` section

2. **Property Mapping**:
   - `transform_code` → `transform.code`
   - `global_table` → `transform.global_table`  
   - `local_table` → `transform.local_table`
   - `node_properties` → `writer.node_properties`
   - `edge_properties` → `writer.edge_properties`

3. **New Features**:
   - Multiple readers support with `readers`
   - Enhanced filter system with more comparison operators
   - SSSOM integration in writer
   - Improved metadata handling

---

**Next Steps: [Transform Code](./transform.md)**