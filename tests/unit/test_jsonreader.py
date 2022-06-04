import gzip
from pathlib import Path

import pytest

from koza.io.reader.json_reader import JSONReader

test_zfin_data = Path(__file__).parents[1] / 'resources' / 'source-files' / 'test_BGI_ZFIN.json.gz'

json_path = ['data', 0,]


def test_normal_case():
    with gzip.open(test_zfin_data, 'rt') as zfin:
        json_reader = JSONReader(zfin, json_path=json_path)
        row = next(json_reader)
        assert row['symbol'] == 'gdnfa'


def test_required_properties():
    with gzip.open(test_zfin_data, 'rt') as zfin:
        json_reader = JSONReader(zfin, ['name', 'basicGeneticEntity.primaryId'], json_path=json_path)
        for row in json_reader:
            print(row)
            assert row['name']
            assert row['basicGeneticEntity']['primaryId']

def test_missing_req_property_raises_exception():
    with gzip.open(test_zfin_data, 'rt') as zfin:
        json_reader = JSONReader(zfin, ['fake_prop'], json_path=json_path)
        with pytest.raises(ValueError):
            next(json_reader)
