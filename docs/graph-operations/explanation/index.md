# Explanation

Understand the concepts, architecture, and design decisions behind graph operations. These pages provide background knowledge that helps you use the tools more effectively.

## Topics

### [Architecture](architecture.md)

Learn how graph operations work under the hood:

- **Why DuckDB?** - Performance benefits of columnar storage and SQL
- **In-memory vs persistent** - When to use each mode
- **Processing pipeline** - How data flows through operations
- **GraphDatabase context manager** - Connection handling and transactions

### [Schema Handling](schema-handling.md)

Understand how graph operations manage different schemas:

- **The schema challenge** - Why different sources have different columns
- **UNION ALL BY NAME** - DuckDB's schema harmonization strategy
- **Auto-detection** - How formats and types are inferred
- **Schema evolution** - Adding columns during append operations
- **NULL handling** - What happens with missing values

### [Data Integrity](data-integrity.md)

Learn about the non-destructive approach to data quality:

- **Philosophy: move, don't delete** - Why problem data is archived
- **Archive tables** - Where problematic data goes
- **Provenance tracking** - How source attribution works
- **Recovery** - Getting data back from archives
- **Why this matters** - Benefits for QC and debugging

### [Biolink Compliance](biolink-compliance.md)

Understand integration with the Biolink model:

- **What is Biolink?** - The knowledge graph standard
- **Required fields** - Minimum columns for valid KGX
- **Multivalued fields** - Handling arrays in node/edge properties
- **Compliance checking** - How validation works
- **Common issues** - Frequent compliance problems and fixes

## Key Concepts

### KGX Format

Knowledge Graph Exchange (KGX) is a standard format for representing knowledge graphs as node and edge tables. Graph operations work with KGX files in TSV, JSONL, or Parquet format.

### DuckDB

DuckDB is an embedded analytical database that provides:

- Fast columnar processing
- SQL query interface
- In-memory and persistent modes
- Excellent compression

### SSSOM

Simple Standard for Sharing Ontological Mappings (SSSOM) is a format for representing identifier mappings. Graph operations use SSSOM files to normalize identifiers during the merge process.

## Design Principles

1. **Non-destructive**: Problem data is moved to archive tables, never deleted
2. **Provenance**: All records track their source file
3. **Flexibility**: Operations work with any valid KGX files
4. **Performance**: DuckDB enables efficient processing of large graphs
5. **SQL access**: You can always query your graph directly
