import gzip
from pathlib import Path

import pytest

from koza.io.reader.jsonl_reader import JSONLReader

test_zfin = (
    Path(__file__).parent.parent / 'resources' / 'source-files' / 'ZFIN_PHENOTYPE_0.jsonl.gz'
)


def test_normal_case():
    with gzip.open(test_zfin, 'rt') as zfin:
        row_limit = 3
        jsonl_reader = JSONLReader(zfin, row_limit=row_limit)
        row = next(jsonl_reader)
        assert len(row) == 6
        assert row['objectId'] == 'ZFIN:ZDB-GENE-011026-1'


def test_required_property():
    with gzip.open(test_zfin, 'rt') as zfin:
        row_limit = 3
        row_count = 1
        jsonl_reader = JSONLReader(zfin, ['objectId'], row_limit=row_limit)
        for row in jsonl_reader:
            row_count += 1
            assert 'objectId' in row
        assert row_count == row_limit


def test_missing_req_property_raises_exception():
    with gzip.open(test_zfin, 'rt') as zfin:
        row_limit = 3
        jsonl_reader = JSONLReader(zfin, ['objectId', 'foobar'], row_limit=row_limit)
        with pytest.raises(ValueError):
            next(jsonl_reader)
