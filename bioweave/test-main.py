from bioweave.io.reader.csv_reader import CSVReader
from bioweave.io.reader.jsonl_reader import JSONLReader

from typing import Iterator

import gzip

from pathlib import Path

from bioweave.model.config.source_config import FieldType

test_file = Path(__file__).parent.parent / 'tests' / 'resources' / 'source-files' / 'string.tsv'
test_zfin = Path(__file__).parent.parent / 'tests' / 'resources' / 'source-files' / 'ZFIN_PHENOTYPE_0.jsonl.gz'

with open(test_file, 'r') as foo:
    field_type_map = {
        'protein1': FieldType.str,
        'protein2': FieldType.str,
        'neighborhood': FieldType.str,
        'fusion': FieldType.str,
        'cooccurence': FieldType.str,
        'coexpression': FieldType.str,
        'experimental': FieldType.str,
        'database': FieldType.str,
        'textmining': FieldType.float,
        'combined_score': FieldType.int
    }
    reader = CSVReader(foo, field_type_map, delimiter=' ')
    for row in reader:
        print(row)

    print(isinstance(reader, Iterator))


with gzip.open(test_zfin, 'rt') as zfin:
    jsonl_reader = JSONLReader(zfin, ['objectId', 'foobar'])
    for row in jsonl_reader:
        print(row)

