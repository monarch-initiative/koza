### Koza

![pupa](docs/img/pupa.png) Data transformation framework

*Disclaimer*: Koza is in pre-alpha

Transform csv, json, and jsonl and converting them to a target
csv, json, or jsonl format based on your dataclass model.  Koza also can output
data in the [KGX format](https://github.com/biolink/kgx/blob/master/specification/kgx-format.md#kgx-format-as-tsv)


##### Highlights

- Author data transforms in semi-declarative Python
- Configure source files, expected columns/json properties and path filters, field filters, and metadata in yaml
- Import mapping files from upstream sources to be used in ingests
(eg id mapping, type mappings)
- Create and use translation tables to map between source and target vocabularies



#### Installation

```
pip install koza
```

#### Getting Started

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

#### Tutorial

Some test commands while we get this up and running:

```bash
koza transform --source examples/string/metadata.yaml 

koza transform --source examples/string-declarative/metadata.yaml 
```

##### Configuration and filters

##### Transform logic

##### Adding a map from a source

##### Adding transform logic

##### Adding a translation table

##### Adding transform logic to a map

##### Ingesting a source with multiple files


#### Overview
Koza's goal is to lower the barrier for domain experts to participate in data transform workflows.

Supports standard streams for chaining transforms with other koza transforms or other command line tools.



What is out of scope for Koza
- Smart fetching (only pull if updated, retries, versioning)
- Batch parallel processing (consider make, snakemake, or a workflow orchestration system)
- Workflow Orchestration (consider Apache airflow, Luigi, Jenkins pipelines, CWL)
- Uploading to a target database

##### Influences:
 - [Dipper](https://github.com/monarch-initiative/dipper)
 - [KG-COVID-19](https://github.com/Knowledge-Graph-Hub/kg-covid-19)
 - [BioThings](https://github.com/biothings)
 
And many others not listed here
