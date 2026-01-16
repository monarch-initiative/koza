# Biolink Compliance

Understanding how graph operations work with the Biolink Model and KGX format.

## Overview

Knowledge graphs in the biomedical domain benefit from standardized data models that enable interoperability and consistent querying. The Biolink Model provides this standardization, defining the vocabulary and structure for representing biological and medical knowledge. Graph operations in Koza are designed to work with Biolink-compliant data in the KGX (Knowledge Graph Exchange) format.

## What is Biolink?

The [Biolink Model](https://biolink.github.io/biolink-model/) is a high-level data model for representing biological and biomedical knowledge graphs. Key aspects include:

- **Standard vocabulary**: Defines consistent terms for node types (categories) and edge types (predicates) across different data sources
- **Node categories**: Hierarchical classification of entities like `biolink:Gene`, `biolink:Disease`, `biolink:ChemicalEntity`
- **Edge predicates**: Standardized relationship types like `biolink:treats`, `biolink:interacts_with`, `biolink:associated_with`
- **Slot definitions**: Properties that can be attached to nodes and edges, such as `name`, `description`, `in_taxon`
- **Maintained by Monarch Initiative**: The model evolves based on community needs and is actively maintained

The Biolink Model uses a LinkML schema definition, which allows tools to programmatically understand field definitions, including whether fields are multivalued, required, or optional.

## KGX Format

KGX (Knowledge Graph Exchange) is the file format that implements the Biolink Model for data exchange. It provides a simple tabular representation suitable for large-scale data processing.

### Node Files

Node files contain entity definitions with columns including:

| Column | Description |
|--------|-------------|
| `id` | Unique identifier (CURIE format, e.g., `HGNC:1234`) |
| `category` | Biolink category (e.g., `biolink:Gene`) |
| `name` | Human-readable name |
| `description` | Detailed description |
| `provided_by` | Data source attribution |

### Edge Files

Edge files define relationships between nodes:

| Column | Description |
|--------|-------------|
| `subject` | Source node ID (CURIE) |
| `predicate` | Relationship type (e.g., `biolink:interacts_with`) |
| `object` | Target node ID (CURIE) |
| `id` | Unique edge identifier |
| `category` | Edge category (e.g., `biolink:Association`) |
| `primary_knowledge_source` | Original data source |

### File Naming Convention

KGX files follow a naming convention that graph operations use for automatic detection:

- `*_nodes.tsv` or `nodes.tsv` - Node files
- `*_edges.tsv` or `edges.tsv` - Edge files

Supported formats include TSV, JSONL, and Parquet.

## Required Fields

For valid KGX data, the following fields are required or strongly recommended:

### Nodes

| Field | Requirement | Notes |
|-------|-------------|-------|
| `id` | **Required** | Must be a valid CURIE (e.g., `HGNC:1234`, `HP:0001234`) |
| `category` | Recommended | Biolink category; defaults to `biolink:NamedThing` if missing |
| `name` | Recommended | Human-readable label for the entity |

### Edges

| Field | Requirement | Notes |
|-------|-------------|-------|
| `subject` | **Required** | CURIE of the source node |
| `predicate` | **Required** | Biolink predicate for the relationship |
| `object` | **Required** | CURIE of the target node |
| `id` | Recommended | Unique identifier for the edge |
| `primary_knowledge_source` | Recommended | Attribution for TRAPI compliance |

## Common Fields

Beyond the required fields, these columns appear frequently in KGX data:

### Node Properties

- **`name`**: Human-readable label
- **`description`**: Longer textual description
- **`provided_by`**: Data source attribution (used for grouping in QC reports)
- **`in_taxon`**: Taxonomic context for biological entities (e.g., `NCBITaxon:9606` for human)
- **`in_taxon_label`**: Human-readable taxon name
- **`xref`**: Cross-references to other databases
- **`synonym`**: Alternative names

### Edge Properties

- **`category`**: Edge category (typically `biolink:Association` or a subclass)
- **`negated`**: Boolean indicating negation of the relationship
- **`knowledge_level`**: TRAPI knowledge level (e.g., `knowledge_assertion`, `logical_entailment`)
- **`agent_type`**: TRAPI agent type (e.g., `manual_agent`, `automated_agent`)
- **`aggregator_knowledge_source`**: Intermediate data aggregators
- **`publications`**: Supporting literature references

## Multivalued Fields

Some Biolink fields can contain multiple values. Graph operations handle these as arrays.

### Common Multivalued Fields

According to the Biolink Model schema, these fields are defined as multivalued:

- **`xref`** / **`xrefs`**: Cross-references to external databases
- **`synonym`** / **`synonyms`**: Alternative names for entities
- **`publications`**: Supporting literature citations
- **`provided_by`**: Multiple data sources contributing to a record
- **`qualifiers`**: Edge qualifiers for nuanced relationships
- **`knowledge_source`**: Knowledge attribution chain
- **`aggregator_knowledge_source`**: Multiple aggregating sources

### Array Handling in Graph Operations

When loading KGX files, graph operations:

1. **Detect array columns** using the Biolink Model schema (via LinkML)
2. **Parse pipe-delimited values** in TSV files (e.g., `PMID:123|PMID:456`)
3. **Store as native arrays** in DuckDB for efficient querying
4. **Preserve array structure** when exporting back to KGX format

```python
# Example: How arrays appear in different formats
# TSV: xref column contains "UniProtKB:P12345|ENSEMBL:ENSG00000139618"
# DuckDB: xref column stored as ['UniProtKB:P12345', 'ENSEMBL:ENSG00000139618']
# JSONL: "xref": ["UniProtKB:P12345", "ENSEMBL:ENSG00000139618"]
```

### Configuration for Multivalued Fields

Some fields that are technically multivalued in Biolink are treated as single-valued in graph operations for practical reasons:

- **`category`**: While nodes can have multiple categories, operations typically use the most specific one
- **`in_taxon`**: Entities usually have a single primary taxon
- **`type`**: Similar to category, treated as single-valued

This behavior can be customized through schema configuration.

## Compliance Checking

Graph operations provide tools to verify Biolink compliance of your data.

### Schema Report Command

Generate a schema analysis report using:

```bash
koza report schema --database my_graph.duckdb --output schema_report.yaml
```

This produces a YAML report containing:

```yaml
metadata:
  operation: schema
  generated_at: '2024-01-15 10:30:00'
  report_version: '1.0'
schema_analysis:
  summary:
    nodes:
      file_count: 5
      unique_columns: 12
      all_columns:
        - id
        - category
        - name
        - in_taxon
        # ... more columns
    edges:
      file_count: 5
      unique_columns: 15
      all_columns:
        - subject
        - predicate
        - object
        # ... more columns
  tables:
    nodes:
      columns:
        - name: id
          type: VARCHAR
        - name: category
          type: VARCHAR
      column_count: 12
      record_count: 50000
    edges:
      columns:
        - name: subject
          type: VARCHAR
        - name: predicate
          type: VARCHAR
        - name: object
          type: VARCHAR
      column_count: 15
      record_count: 100000
  biolink_compliance:
    status: compliant
    compliance_percentage: 95.5
    missing_fields: []
    extension_fields:
      - custom_score
      - source_version
```

### What Compliance Checking Validates

The schema report analyzes:

1. **Required fields present**: Ensures `id` for nodes and `subject`/`predicate`/`object` for edges
2. **Column data types**: Validates appropriate types (VARCHAR for IDs, arrays for multivalued fields)
3. **Biolink slot coverage**: Identifies which columns map to standard Biolink slots
4. **Extension fields**: Lists custom columns not defined in the Biolink Model
5. **Schema consistency**: Detects variations in column structure across source files

### Using with Join Operations

Schema reports are automatically generated during join operations when `schema_reporting=True`:

```bash
koza join --nodes data/*_nodes.tsv --edges data/*_edges.tsv \
    --output merged.duckdb
# Produces: merged_schema_report.yaml
```

## Common Compliance Issues

### Missing Required Fields

**Problem**: Edges missing `subject`, `predicate`, or `object` columns.

```
Error: Required edge columns missing: ['predicate']
```

**Solution**: Ensure your source data includes all required columns before joining.

### Invalid Predicates

**Problem**: Using predicates not defined in the Biolink Model.

```yaml
# Problematic:
predicate: custom:related_to

# Correct:
predicate: biolink:related_to
```

**Solution**: Map custom predicates to standard Biolink predicates, or use `biolink:related_to` as a generic fallback.

### Non-Standard Categories

**Problem**: Node categories that don't exist in Biolink.

```yaml
# Problematic:
category: MyDatabase:ProteinEntity

# Correct:
category: biolink:Protein
```

**Solution**: Map source categories to appropriate Biolink categories. Use the category hierarchy to find the most specific valid category.

### Malformed CURIEs

**Problem**: IDs that don't follow CURIE format.

```yaml
# Problematic:
id: 12345
id: http://example.org/entity/12345

# Correct:
id: EXAMPLE:12345
```

**Solution**: Ensure all IDs follow the `prefix:local_id` format. Use normalization to standardize IDs.

### Missing Provenance

**Problem**: Data without source attribution makes it difficult to track data lineage.

```yaml
# Missing provenance - harder to debug issues:
- id: HGNC:1234
  category: biolink:Gene
  name: BRCA1

# With provenance:
- id: HGNC:1234
  category: biolink:Gene
  name: BRCA1
  provided_by: infores:hgnc
```

**Solution**: Use the `--generate-provided-by` flag during join/merge operations to automatically add provenance from filenames.

### Schema Mismatches Across Sources

**Problem**: Different source files have different column structures.

```yaml
schema_analysis:
  # File A has 10 columns, File B has 15 columns
  # This causes NULL values in merged data
```

**Solution**: The join operation handles this automatically by creating a unified schema. Review the schema report to understand which columns come from which sources.

## Best Practices

1. **Validate early**: Run schema reports on source files before large merge operations
2. **Use standard prefixes**: Stick to well-known CURIE prefixes (HGNC, HP, MONDO, etc.)
3. **Include provenance**: Always populate `provided_by` or `primary_knowledge_source`
4. **Document extensions**: If using custom columns, document their purpose and expected values
5. **Regular compliance checks**: Integrate schema validation into your data pipeline

## Related Documentation

- [Schema Handling](schema-handling.md) - How graph operations manage schema evolution
- [Data Integrity](data-integrity.md) - Ensuring data quality during operations
- [Generate Reports How-To](../how-to/generate-reports.md) - Practical guide to report generation
