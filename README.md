# Koza - Knowledge Graph Transformation and Operations Toolkit

[![Pyversions](https://img.shields.io/pypi/pyversions/koza.svg)](https://pypi.python.org/pypi/koza)
[![PyPi](https://img.shields.io/pypi/v/koza.svg)](https://pypi.python.org/pypi/koza)
![Github Action](https://github.com/monarch-initiative/koza/actions/workflows/test.yaml/badge.svg)

![pupa](docs/img/pupa.png)

[**Documentation**](https://koza.monarchinitiative.org/)

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

See the [Koza documentation](https://koza.monarchinitiative.org/) for complete usage information.

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
