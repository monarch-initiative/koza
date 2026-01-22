# Schema Handling

## Overview

When building knowledge graphs from multiple sources, handling different schemas is a common challenge. Each data source may use different columns, different naming conventions, and different data types. Graph operations use DuckDB's schema harmonization features to combine these heterogeneous files into a unified graph.

This document explains how schema handling works, from format detection through schema evolution, so you can understand what happens when your files have different columns.

## The Schema Challenge

### Why Different KGX Files Have Different Columns

Knowledge graph data comes from many different sources, and each source may have different characteristics:

**Different data sources**: A gene annotation database exports different fields than a disease ontology. One might include `taxon` and `chromosome`, while another includes `definition` and `synonyms`.

**Different Biolink slots used**: The Biolink model defines many optional slots for nodes and edges. A protein interaction dataset might use `has_evidence` and `supporting_publications`, while a chemical database uses `has_chemical_formula` and `molecular_weight`.

**Optional vs required fields**: While KGX defines core fields like `id`, `name`, `category` for nodes and `subject`, `predicate`, `object` for edges, most other fields are optional. Different sources populate different subsets.

**Custom extensions**: Some data sources include custom columns beyond the Biolink model, such as source-specific identifiers, confidence scores, or annotation metadata.

### Example: Schema Variation in Practice

Consider combining three node files:

```
# gene_nodes.tsv (5 columns)
id    name    category    taxon    chromosome

# disease_nodes.tsv (4 columns)
id    name    category    definition

# chemical_nodes.tsv (6 columns)
id    name    category    formula    smiles    molecular_weight
```

When these files are combined, the result must include all columns from all sources, with appropriate handling for missing values.

## UNION ALL BY NAME

### DuckDB's Schema Harmonization Strategy

Graph operations use DuckDB's `UNION ALL BY NAME` feature to combine files with different schemas. This is the key mechanism that makes heterogeneous file handling possible.

### How It Works

**Columns matched by name, not position**: Unlike traditional `UNION ALL` which requires identical column order, `UNION ALL BY NAME` matches columns by their names. This means files can have columns in any order.

**Missing columns filled with NULL**: When a file lacks a column that exists in another file, DuckDB fills those cells with `NULL`. No data is lost.

**All columns from all sources preserved**: The final table includes every column from every source file. No manual schema mapping is required.

### Example

```sql
-- DuckDB automatically handles schema differences
CREATE TABLE nodes AS
SELECT * FROM temp_genes
UNION ALL BY NAME
SELECT * FROM temp_diseases
UNION ALL BY NAME
SELECT * FROM temp_chemicals
```

Result schema: `id`, `name`, `category`, `taxon`, `chromosome`, `definition`, `formula`, `smiles`, `molecular_weight`

For genes: `definition`, `formula`, `smiles`, `molecular_weight` will be `NULL`
For diseases: `taxon`, `chromosome`, `formula`, `smiles`, `molecular_weight` will be `NULL`
For chemicals: `taxon`, `chromosome`, `definition` will be `NULL`

## Format Auto-Detection

### How Format Is Detected

Graph operations detect file formats automatically. The `FileSpec` model handles this through field validators.

### File Extension Detection

The format is detected from the file extension:

| Extension | Format |
|-----------|--------|
| `.tsv`, `.txt` | TSV (tab-separated values) |
| `.jsonl`, `.json` | JSONL (JSON Lines) |
| `.parquet` | Parquet |

### Compression Detection

The system handles compressed files by first stripping the compression extension, then detecting the underlying format:

| File | Detected Format |
|------|-----------------|
| `nodes.tsv.gz` | TSV (compressed) |
| `edges.jsonl.bz2` | JSONL (compressed) |
| `data.parquet.xz` | Parquet (compressed) |

DuckDB reads compressed files without manual decompression.

### File Type Detection

The system also auto-detects whether a file contains nodes or edges based on filename patterns:

- Files containing `_nodes.` or starting with `nodes.` are detected as node files
- Files containing `_edges.` or starting with `edges.` are detected as edge files

## Type Inference

### How Column Types Are Determined

DuckDB performs type inference when reading files. The behavior varies by format:

**TSV files**: By default, graph operations read TSV files with `all_varchar=true`, treating all columns as text. This avoids data loss from type mismatches and handles mixed-type columns consistently.

**JSONL files**: DuckDB infers types from the JSON structure. Arrays become `VARCHAR[]` (array of strings), numbers become appropriate numeric types, and strings remain `VARCHAR`. The option `convert_strings_to_integers=false` prevents UUID-like strings from being incorrectly parsed as integers.

**Parquet files**: Types are preserved exactly as stored in the Parquet schema, since Parquet is a typed format.

### Array Detection for Multivalued Fields

Graph operations identify multivalued fields (like `synonym`, `xref`, `publications`) and convert them appropriately:

1. **Schema-based detection**: The system consults the Biolink model schema to determine which fields are defined as multivalued
2. **Fallback list**: When the schema is unavailable, a hardcoded list of common KGX multivalued fields is used
3. **Transformation**: For TSV files, pipe-delimited values (`value1|value2|value3`) are converted to arrays

```python
# Fields that are always treated as single-valued (overrides schema)
FORCE_SINGLE_VALUED_FIELDS = {"category", "in_taxon", "type"}

# Fallback multivalued fields when schema unavailable
KGX_MULTIVALUED_FIELDS_FALLBACK = {
    "xref", "synonym", "publications", "provided_by",
    "qualifiers", "knowledge_source", "has_evidence", ...
}
```

## Schema Evolution with Append

### How New Columns Are Added

The append operation supports schema evolution, allowing you to add files with new columns to an existing database.

### The Process

1. **Load new file into temp table**: The new file is loaded with its full schema
2. **Compare schemas**: The temp table schema is compared to the existing table
3. **ALTER TABLE ADD COLUMN**: Any columns in the new file that do not exist in the target table are added via `ALTER TABLE`
4. **Insert with UNION ALL BY NAME**: Data is inserted using schema-compatible union

```python
# Schema evolution in append operation
new_columns = set(file_columns.keys()) - set(existing_schema.keys())
for col_name in new_columns:
    col_type = file_columns[col_name]
    db.conn.execute(f"ALTER TABLE {table_type} ADD COLUMN {col_name} {col_type}")
```

### NULL Backfill for Existing Rows

When a new column is added to an existing table, all existing rows receive `NULL` for that column. DuckDB does this automatically.

### Example

```
# Original database has nodes with: id, name, category

# New file has: id, name, category, taxon, description

# After append:
# - taxon and description columns are added
# - Original nodes have NULL for taxon and description
# - New nodes have all five fields populated
```

## NULL Handling

### What Happens with Missing Values

NULL values occur during schema harmonization. Here is how they flow through operations:

**During join**: Missing columns are filled with `NULL` via `UNION ALL BY NAME`

**During append**: New columns in existing rows are `NULL`; missing columns in new rows are `NULL`

**During export**: `NULL` values are preserved in the output format:
- TSV: Empty cell (no value between tabs)
- JSONL: Field omitted from the JSON object
- Parquet: Native NULL representation

**In queries**: Use `IS NULL` / `IS NOT NULL` to filter, or `COALESCE()` to provide defaults

### NULLs vs Empty Arrays

For multivalued fields, there is a distinction:

- `NULL`: The field has no value (not provided)
- `[]` (empty array): The field was provided but contains no values
- `['value']`: The field contains one or more values

Graph operations preserve this distinction when possible. TSV format cannot distinguish between `NULL` and empty string.

## Best Practices

### Tips for Maintaining Clean Schemas

**Use consistent column naming**: Follow Biolink naming conventions (`snake_case`) across all your source files.

**Document your extensions**: If you add custom columns beyond Biolink, document what they contain.

**Validate before joining**: Use the schema report feature (`--schema-reporting`) to analyze schemas before combining files.

**Consider output format**: If schema consistency matters for downstream tools, consider exporting to Parquet which preserves exact types.

**Handle multivalued fields consistently**: Use pipe-delimited format (`value1|value2`) in TSV files for multivalued fields.

**Review NULL patterns**: After joining, query for NULL patterns to understand data coverage:

```sql
-- Find columns with high NULL rates
SELECT
    'taxon' as column_name,
    COUNT(*) as total,
    COUNT(taxon) as non_null,
    ROUND(100.0 * COUNT(taxon) / COUNT(*), 1) as coverage_pct
FROM nodes
```

**Use provided_by for provenance**: Enable `generate_provided_by` (default) to track which source each record came from. This allows investigation of schema differences by source.
