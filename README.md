### Koza

![pupa](docs/img/pupa.png) Data ingest framework for the Biolink model

*Disclaimer*: Koza is in pre-alpha


##### Highlights
Koza allows you to:

- Author data transforms in semi-declarative Python

- Configure source files, expected columns/json properties and path filters,
field filters, and metadata in yaml

- Import mapping files from upstream sources to be used in ingests
(eg id mapping, type mappings)

- Translation tables to map between source vocabulary and ontology terms

Koza supports processing csv, json, and jsonl and converting them to the
[Biolink model](https://biolink.github.io/biolink-model/)

Koza outputs data in the
[KGX tsv format](https://github.com/biolink/kgx/blob/master/specification/kgx-format.md#kgx-format-as-tsv)


#### Installation

```
pip install koza
```

#### Getting Started

Send a local or remove csv file through Koza to get some basic information (headers, number of rows)

```bash
koza run \
  --file https://raw.githubusercontent.com/monarch-initiative/koza/dev/tests/resources/source-files/string.tsv \
  --delimiter ' '
```

Sending a json or jsonl formatted file will confirm if the file is valid json or jsonl
```bash
koza run \
  --file ./examples/data/ZFIN_PHENOTYPE_0.jsonl.gz \
  --format jsonl
```

```bash
koza run \
  --file /examples/data/ddpheno.json.gz \
  --format json
```

#### Tutorial

##### Configuration and filters

##### Transform logic

##### Adding a map from a source

##### Adding transform logic

##### Adding a translation table

##### Adding transform logic to a map

##### Ingesting a source with multiple files

##### Ingesting multiple sources

Koza does not have out of the box support for ingesting a batch of sources.  For this we
recommend creating a make or [snakemake](https://snakemake.readthedocs.io/en/stable/) pipeline.
TODO, point to example


#### Philosophy
Koza's goal is to lower the barrier for domain experts to participate in data transform workflows.

As a library, our goal is to do transformations well, and let other tools tackle downloading,
storage/caching raw data files, batch parallel processing, and uploading to a target database.
Koza does the T in ETL (Extract Transform Load).

For downloading source data we're currently using gnu make + wget, see
[DipperCache](https://github.com/monarch-initiative/DipperCache) as an example.

For creating batch workflows to ingest multiple sources we'll aim to use
make or [snakemake](https://snakemake.readthedocs.io/en/stable/)

For uploading KGX TSVs to a target database we're using [KGX](https://github.com/biolink/kgx)

##### Influences:
 - [Dipper](https://github.com/monarch-initiative/dipper)
 - [KG-COVID-19](https://github.com/Knowledge-Graph-Hub/kg-covid-19)
 - [BioThings](https://github.com/biothings)
 
And many others not listed here