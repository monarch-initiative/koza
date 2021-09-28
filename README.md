### Koza

![pupa](docs/img/pupa.png) Data transformation framework

*Disclaimer*: Koza is in beta; we are looking for beta testers

Transform csv, json, yaml, jsonl, and xml and converting them to a target
csv, json, or jsonl format based on your dataclass model.  Koza also can output
data in the [KGX format](https://github.com/biolink/kgx/blob/master/specification/kgx-format.md#kgx-format-as-tsv)

**Documentation**: https://koza.monarchinitiative.org/

##### Highlights

- Author data transforms in semi-declarative Python
- Configure source files, expected columns/json properties and path filters, field filters, and metadata in yaml
- Create or import mapping files to be used in ingests (eg id mapping, type mappings)
- Create and use translation tables to map between source and target vocabularies


#### Installation

```
pip install koza
```

#### Getting Started

Send a local or remove csv file through Koza to get some basic information (headers, number of rows)

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

###### Example: transforming StringDB

```bash
koza transform --source examples/string/protein-links-detailed.yaml --global-table examples/translation_table.yaml 

koza transform --source examples/string-declarative/protein-links-detailed.yaml --global-table examples/translation_table.yaml
```
