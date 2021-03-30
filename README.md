### Koza

![pupa](docs/img/pupa.png) Data ingest framework for the Biolink model

*Disclaimer*: Koza is in pre-alpha


##### Highlights
Koza allows you to:

- Author transforms with dataclasses in semi-declarative Python
- Configure filters, metadata, and data mappings in yaml
- Import and optionally transform mapping files
- Create an ETL pipeline for multiple sources

While Koza aims to support a declarative programming paradigm, it
also supports procedural programming constructs

TODO describe assumptions for source data


###### What is out of scope mid term?

- Models other than Biolink

#### Installation

```
pip install koza
```

#### Getting Started

Send a TSV file through Koza to get some basic information (headers, number of rows)

```bash
koza run \
  --file https://raw.githubusercontent.com/monarch-initiative/koza/dev/tests/resources/source-files/string.tsv \
  --delimiter ' '
```

Or a jsonl formatted file
```bash
koza run \
  --file ./tests/resources/source-files/ZFIN_PHENOTYPE_0.jsonl.gz \
  --format jsonl
```

#### A Small Example - adding configuration and filters


#### A Full Example - Adding transform logic and maps


##### Adding Transform Logic


##### Adding A Map
TODO


##### Example of a procedural transform
TODO
