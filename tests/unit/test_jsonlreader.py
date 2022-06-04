import gzip
from pathlib import Path

import pytest

from koza.io.reader.jsonl_reader import JSONLReader

test_zfin_data = Path(__file__).parents[1] / 'resources' / 'source-files' / 'ZFIN_PHENOTYPE_0.jsonl.gz'

def test_normal_case():
    with gzip.open(test_zfin_data, 'rt') as zfin:
        jsonl_reader = JSONLReader(zfin)
        row = next(jsonl_reader)
        assert len(row) == 6

        assert row['objectId'] == 'ZFIN:ZDB-GENE-011026-1'


def test_required_property():
    with gzip.open(test_zfin_data, 'rt') as zfin:
        jsonl_reader = JSONLReader(zfin, required_properties = ['objectId', 'evidence.publicationId'])
        for row in jsonl_reader:
            # assert len(row) == 1  # removed subsetter
            print(row)
            assert 'objectId' in row
            assert row['evidence']['publicationId']


def test_missing_req_property_raises_exception():
    with gzip.open(test_zfin_data, 'rt') as zfin:
        jsonl_reader = JSONLReader(zfin, ['objectId', 'foobar'])
        with pytest.raises(ValueError):
            next(jsonl_reader)
