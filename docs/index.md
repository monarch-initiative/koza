## Koza Data Transformation Framework

![pupa](img/pupa.png)

*Disclaimer*: Koza is in beta

Transform csv, json, jsonl, and yaml - converting them to a target
csv, json, or jsonl format based on your dataclass model.  Koza also can output
data in the [KGX format](https://github.com/biolink/kgx/blob/master/specification/kgx-format.md#kgx-format-as-tsv)


##### Highlights

- Author data transforms in semi-declarative Python
- Configure source files, expected columns/json properties and path filters, field filters, and metadata in yaml
- Create or import mapping files to be used in ingests (eg id mapping, type mappings)
- Create and use translation tables to map between source and target vocabularies


### Installation

```
pip install koza
```

### Getting Started

#### Writing an ingest

[Ingest Configuration](ingest_configuration.md)

#### Running an ingest

Send a local or remove csv file through Koza to get some basic information (headers, number of rows)

```bash
koza validate \
  --file https://raw.githubusercontent.com/monarch-initiative/koza/dev/tests/resources/source-files/string.tsv \
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

##### Example: transforming StringDB

```bash
koza transform --source examples/string/metadata.yaml 

koza transform --source examples/string-declarative/metadata.yaml 
```
#### Running an ingest from within a python script

Executing a koza transform from within a python script can be done by calling transform_source from koza.cli_runner

```python
from koza.cli_runner import transform_source

transform_source("./examples/string/protein-links-detailed.yaml",
                 "output", "tsv", "./examples/translation_table.yaml", None)
```
