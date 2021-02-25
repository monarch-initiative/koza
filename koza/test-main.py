# test

from koza.io.utils import open_resource
from koza.io.reader.csv_reader import CSVReader
from pathlib import Path
from typing import TextIO
from io import IOBase
import inspect

p = Path(Path('setup.py'))

foo = "https://raw.githubusercontent.com/monarch-inititiave/koza/dev/tests/resources/source-files/string.tsv"
#foo = "https://github.com/monarch-inititiave/koza/raw/dev/tests/resources/source-files/ZFIN_PHENOTYPE_0.jsonl.gz"
with open_resource(foo) as bar:
    reader = CSVReader(bar, delimiter=' ')
    for row in reader:
        pass
