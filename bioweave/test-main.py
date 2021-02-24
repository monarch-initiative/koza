# test

from bioweave.io.utils import open_resource
from bioweave.io.reader.csv_reader import CSVReader
from pathlib import Path
from typing import TextIO
from io import IOBase
import inspect

p = Path(Path('setup.py'))

foo = "https://raw.githubusercontent.com/kshefchek/bioweave/dev/tests/resources/source-files/string.tsv"
#foo = "https://github.com/kshefchek/bioweave/raw/dev/tests/resources/source-files/ZFIN_PHENOTYPE_0.jsonl.gz"
with open_resource(foo) as bar:
    reader = CSVReader(bar, delimiter=' ')
    for row in reader:
        print(row)
