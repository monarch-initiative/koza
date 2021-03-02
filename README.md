### Koza

![pupa](docs/img/pupa.png) Data ingest framework for the Biolink model

*Disclaimer*: Koza is in pre-alpha

Author declarative transforms with dataclasses in the spirit of a DSL but in vanilla 
Python3


#### Installation

```
pip install koza
```

#### Getting Started

Send a TSV file through Koza to get some basic information (headers, row/column length)

```bash
koza run --file https://raw.githubusercontent.com/monarch-initiative/koza/dev/tests/resources/source-files/string.tsv --delimiter ' '
```

Or a local file
```bash
koza run --file ./tests/resources/source-files/ZFIN_PHENOTYPE_0.jsonl.gz --format jsonl
```

#### A Small Example - adding configuration and filters


TODO example using string


#### A Full Example - Adding transform logic and maps

##### Adding Transform Logic

##### Adding A Map
/home/kshefchek/git/koza/examples/data
TODO example using string
