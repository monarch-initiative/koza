from bioweave.io.reader.csv_reader import CSVReader

from pathlib import Path

test_file = Path(__file__).parent.parent / 'tests' / 'resources' / 'source-files' / 'string.tsv'

with open(test_file, 'r') as foo:
    reader = CSVReader(foo, delimiter=' ')
    for row in reader:
        print(row)
