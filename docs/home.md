# Koza 

[![Pyversions](https://img.shields.io/pypi/pyversions/koza.svg)](https://pypi.python.org/pypi/koza) ![](https://github.com/monarch-initiative/koza/actions/workflows/build.yml/badge.svg) [![PyPi](https://img.shields.io/pypi/v/koza.svg)](https://pypi.python.org/pypi/koza)

**A data transformation framework**  
*Disclaimer: Koza is in beta; we are looking for beta testers*

### Overview

Koza is a data transformation framework which allows you to write semi-declarative "**ingests**"

  - Transform csv, json, yaml, jsonl, or xml source data, converting them to a target csv, json, or jsonl format based on your dataclass model.  
  - Koza also can output data in the <a href="https://github.com/biolink/kgx/blob/master/specification/kgx-format.md#kgx-format-as-tsv" target="_blank">KGX format</a>
  - Write data transforms in semi-declarative Python
  - Configure source files, expected columns/json properties and path filters, field filters, and metadata in yaml
  - Create or import mapping files to be used in ingests (eg. id mapping, type mappings)
  - Create and use translation tables to map between source and target vocabularies

### Installation
Koza is available on PyPi and can be installed via pip:
```
pip install koza
```

**Now let's take a look at how to use Koza! First step: [Setup and usage](Usage/configuring_ingests.md)**

<img src='../img/pupa.png' width='50%' style='display: block; margin-left: auto; margin-right: auto;'>
