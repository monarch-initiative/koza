import gzip
from pathlib import Path

import pytest

from koza.io.reader.json_reader import JSONReader

test_ddpheno = Path(__file__).parents[1] / 'resources' / 'source-files' / 'ddpheno.json.gz'

json_path = ['graphs', 0, 'nodes']


def test_normal_case():
    with gzip.open(test_ddpheno, 'rt') as ddpheno:
        json_reader = JSONReader(ddpheno, json_path=json_path, row_limit=3)
        row = next(json_reader)
        assert row['id'] == 'http://purl.obolibrary.org/obo/DDPHENO_0001198'


def test_required_properties():
    with gzip.open(test_ddpheno, 'rt') as ddpheno:
        row_limit=3
        row_count = 0
        json_reader = JSONReader(ddpheno, ['id'], json_path=json_path, row_limit=row_limit)
        for row in json_reader:
            row_count += 1
            assert 'id' in row
        assert row_count == row_limit


def test_missing_req_property_raises_exception():
    with gzip.open(test_ddpheno, 'rt') as ddpheno:
        json_reader = JSONReader(ddpheno, ['fake_prop'], json_path=json_path, row_limit=3)
        with pytest.raises(ValueError):
            next(json_reader)
