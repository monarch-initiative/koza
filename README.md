# Koza - Knowledge Graph Transformation and Operations Toolkit

[![Pyversions](https://img.shields.io/pypi/pyversions/koza.svg)](https://pypi.python.org/pypi/koza)
[![PyPi](https://img.shields.io/pypi/v/koza.svg)](https://pypi.python.org/pypi/koza)
![Github Action](https://github.com/monarch-initiative/koza/actions/workflows/test.yaml/badge.svg)

![pupa](docs/img/pupa.png)  

[**Documentation**](https://koza.monarchinitiative.org/)

_Disclaimer_: Koza is in beta - we are looking for testers!

## Overview

Koza is a Python library and CLI tool for transforming biomedical data and performing graph operations on Knowledge Graph Exchange (KGX) files. It provides two main capabilities:

### 📊 **Graph Operations** (New!)
Powerful DuckDB-based operations for KGX knowledge graphs:
- **Join** multiple KGX files with schema harmonization
- **Split** files by field values with format conversion  
- **Prune** dangling edges and handle singleton nodes
- **Append** new data to existing databases with schema evolution
- **Multi-format support** for TSV, JSONL, and Parquet files

### 🔄 **Data Transformation** (Core)
Transform biomedical data sources into KGX format:
- Transform csv, json, yaml, jsonl, and xml to target formats
- Output in [KGX format](https://github.com/biolink/kgx/blob/master/specification/kgx-format.md#kgx-format-as-tsv)
- Write data transforms in semi-declarative Python
- Configure source files, columns/properties, and metadata in YAML
- Create mapping files and translation tables between vocabularies

## Installation
Koza is available on PyPi and can be installed via pip/pipx:
```
[pip|pipx] install koza
```

## Usage

### Quick Start with Graph Operations

Koza's graph operations work seamlessly across multiple KGX formats (TSV, JSONL, Parquet):

```bash
# Join multiple KGX files into a unified database
koza join --nodes genes.tsv pathways.jsonl --edges interactions.parquet --output merged_graph.duckdb

# Prune dangling edges and handle singleton nodes
koza prune --database merged_graph.duckdb --keep-singletons

# Append new data to existing database with schema evolution
koza append --database merged_graph.duckdb --nodes new_genes.tsv --edges new_interactions.jsonl

# Split database by source with format conversion
koza split --database merged_graph.duckdb --split-on provided_by --output-format parquet
```

**NOTE: As of version 0.2.0, there is a new method for getting your ingest's `KozaApp` instance. Please see the [updated documentation](https://koza.monarchinitiative.org/Usage/configuring_ingests/#transform-code) for details.**

See the [Koza documentation](https://koza.monarchinitiative.org/) for complete usage information

### Examples

#### Validate

Give Koza a local or remote csv file, and get some basic information (headers, number of rows)

```bash
koza validate \
  --file https://raw.githubusercontent.com/monarch-initiative/koza/main/examples/data/string.tsv \
  --delimiter ' '
```

Sending a json or jsonl formatted file will confirm if the file is valid json or jsonl

```bash
koza validate \
  --file ./examples/data/ZFIN_PHENOTYPE_0.jsonl.gz \
  --format jsonl
```

```bash
koza validate \
  --file ./examples/data/ddpheno.json.gz \
  --format json
```

#### Transform

Run the example ingest, "string/protein-links-detailed"
```bash
koza transform \
  --source examples/string/protein-links-detailed.yaml \
  --global-table examples/translation_table.yaml

koza transform \
  --source examples/string-declarative/protein-links-detailed.yaml \
  --global-table examples/translation_table.yaml
```

**Note**: 
  Koza expects a directory structure as described in the above example  
  with the source config file and transform code in the same directory: 
  ```
  .
  ├── ...
  │   ├── your_source
  │   │   ├── your_ingest.yaml
  │   │   └── your_ingest.py
  │   └── some_translation_table.yaml
  └── ...
  ```

#### Graph Operations

Create and manipulate knowledge graphs from existing KGX files:

```bash
# Join heterogeneous KGX files with automatic schema harmonization
koza join \
  --nodes genes.tsv proteins.jsonl pathways.parquet \
  --edges gene_protein.tsv protein_pathway.jsonl \
  --output unified_graph.duckdb \
  --schema-report

# Clean up graph integrity issues
koza prune \
  --database unified_graph.duckdb \
  --keep-singletons \
  --dry-run  # Preview changes before applying

# Incrementally add new data with schema evolution
koza append \
  --database unified_graph.duckdb \
  --nodes new_genes.tsv updated_pathways.jsonl \
  --deduplicate \
  --show-progress

# Export subsets with format conversion
koza split \
  --database unified_graph.duckdb \
  --split-on provided_by \
  --output-format parquet \
  --output-dir ./split_graphs
```

## Key Features

### 🔧 **Multi-Format Support**
- Native support for TSV, JSONL, and Parquet KGX files
- Automatic format detection and conversion
- Mixed-format operations in single commands

### 🛡️ **Schema Flexibility**
- Automatic schema harmonization across heterogeneous files
- Schema evolution with backward compatibility  
- Comprehensive schema reporting and validation

### ⚡ **High Performance**
- DuckDB-powered operations for fast bulk processing
- Memory-efficient handling of large knowledge graphs
- Parallel processing and streaming where possible

### 🔍 **Rich CLI Experience**
- Progress indicators for long-running operations
- Detailed statistics and operation summaries
- Dry-run modes for safe operation preview

### 🧹 **Data Integrity**
- Dangling edge detection and preservation
- Duplicate detection and removal strategies
- Non-destructive operations with data archiving