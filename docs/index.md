# Koza - a data transformation framework

## Overview

Koza is a data transformation framework which allows you to write semi-declarative "**ingests**"

- Transform csv, json, yaml, jsonl, or xml source data, converting them to a target csv, json, or jsonl format based on your dataclass model.  
- Koza also can output data in the <a href="https://github.com/biolink/kgx/blob/master/specification/kgx-format.md#kgx-format-as-tsv" target="_blank">KGX format</a>
- Write data transforms in semi-declarative Python
- Configure source files, expected columns/json properties and path filters, field filters, and metadata in yaml
- Create or import mapping files to be used in ingests (eg. id mapping, type mappings)
- Create and use translation tables to map between source and target vocabularies

## Installation
Koza is available on PyPi and can be installed via pip:
```
pip install koza
```

## Usage

See the [Ingests](./Usage/ingests.md) page for information on how to configure ingests for koza to use.

Koza can be used as a Python library, or via the command line.  
[CLI commands](./Usage/CLI.md) are available for validating and transforming data.  
See the [API](./Usage/API.md) page for information on using Koza as a library.

Koza also includes some examples to help you get started (see `koza/examples`).
### Basic Examples

!!! list "Validate"

    Give Koza a local or remote csv file, and get some basic information (headers, number of rows)

    ```bash
    koza validate \
      --file ./examples/data/string.tsv \
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
      --format json \
      --compression gzip
    ```

!!! list "Transform"

    Try one of Koza's example ingests:  
    ```bash
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
      │   ├── some_source
      │   │   ├── your_ingest.yaml
      │   │   └── your_ingest.py
      │   └── some_translation_table.yaml
      └── ...
      ```
