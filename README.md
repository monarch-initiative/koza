# Koza - a data transformation framework  

[![Pyversions](https://img.shields.io/pypi/pyversions/koza.svg)](https://pypi.python.org/pypi/koza)
[![PyPi](https://img.shields.io/pypi/v/koza.svg)](https://pypi.python.org/pypi/koza)
![Github Action](https://github.com/monarch-initiative/koza/actions/workflows/build.yml/badge.svg)

![pupa](docs/img/pupa.png)  

[**Documentation**](https://koza.monarchinitiative.org/  )

_Disclaimer_: Koza is in beta; we are looking for beta testers

### Overview
  - Transform csv, json, yaml, jsonl, and xml and converting them to a target csv, json, or jsonl format based on your dataclass model.  
  - Koza also can output data in the [KGX format](https://github.com/biolink/kgx/blob/master/specification/kgx-format.md#kgx-format-as-tsv)
  - Write data transforms in semi-declarative Python
  - Configure source files, expected columns/json properties and path filters, field filters, and metadata in yaml
  - Create or import mapping files to be used in ingests (eg id mapping, type mappings)
  - Create and use translation tables to map between source and target vocabularies

### Installation
Koza is available on PyPi and can be installed via pip/pipx:
```
[pip|pipx] install koza
```

### Usage

**NOTE: As of version 0.2.0, there is a new method for getting your ingest's `KozaApp` instance. Please see the [updated documentation](https://koza.monarchinitiative.org/Usage/configuring_ingests/#transform-code) for details.**

See the [Koza documentation](https://koza.monarchinitiative.org/) for usage information

### Try the Examples

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
  --format json \
  --compression gzip
```

#### Transform

Run the example ingest, "string/protein-links-detailed"
```bash
koza transform --source examples/string/protein-links-detailed.yaml --global-table examples/translation_table.yaml

koza transform --source examples/string-declarative/protein-links-detailed.yaml --global-table examples/translation_table.yaml
```
note: koza expects a directory structure as described in the above example (examples/ingest_name/ingest.yaml)