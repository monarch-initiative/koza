# test

from pathlib import Path

from koza.io.reader.csv_reader import CSVReader
from koza.io.utils import open_resource

foo = "https://raw.githubusercontent.com/monarch-initiative/koza/dev/tests/resources/source-files/string.tsv"
# foo = "https://github.com/monarch-initiative/koza/raw/dev/tests/resources/source-files/ZFIN_PHENOTYPE_0.jsonl.gz"
with open_resource(foo) as bar:
    reader = CSVReader(bar, delimiter=' ')
    for row in reader:
        print(row)
