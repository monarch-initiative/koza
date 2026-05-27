# Explanation

This section covers concepts, architecture, and design decisions behind graph operations.

## Topics

### [Architecture](architecture.md)

Describes how graph operations are structured:

- **Why DuckDB?** - Columnar storage and SQL for graph processing
- **In-memory vs persistent** - Different operational modes
- **Processing pipeline** - Data flow through operations
- **GraphDatabase context manager** - Connection handling and transactions

### [Schema Handling](schema-handling.md)

Covers how graph operations manage different schemas:

- **The schema challenge** - Why different sources have different columns
- **UNION ALL BY NAME** - DuckDB's schema harmonization approach
- **Auto-detection** - How formats and types are inferred
- **Schema evolution** - Adding columns during append operations
- **NULL handling** - Treatment of missing values

### [Data Integrity](data-integrity.md)

Explains the non-destructive approach to data quality:

- **Philosophy: move, don't delete** - Why problem data is archived
- **Archive tables** - Where problematic data is stored
- **Provenance tracking** - How source attribution works
- **Recovery** - Retrieving data from archives
- **Use cases** - QC and debugging scenarios

### [Biolink Compliance](biolink-compliance.md)

Describes integration with the Biolink model:

- **What is Biolink?** - The knowledge graph standard
- **Required fields** - Minimum columns for valid KGX
- **Multivalued fields** - Arrays in node/edge properties
- **Compliance checking** - How validation works
- **Common issues** - Frequent compliance problems and fixes

## Key Concepts

### KGX Format

Knowledge Graph Exchange (KGX) is a standard format for representing knowledge graphs as node and edge tables. Graph operations work with KGX files in TSV, JSONL, or Parquet format.

### DuckDB

DuckDB is an embedded analytical database with:

- Columnar processing
- SQL query interface
- In-memory and persistent modes
- Data compression

### SSSOM

Simple Standard for Sharing Ontological Mappings (SSSOM) is a format for representing identifier mappings. Graph operations use SSSOM files to normalize identifiers during the merge process.

## Design Principles

1. **Non-destructive**: Problem data is moved to archive tables, not deleted
2. **Provenance**: All records track their source file
3. **Flexibility**: Operations work with any valid KGX files
4. **Performance**: DuckDB handles processing of large graphs
5. **SQL access**: Graphs can be queried directly
