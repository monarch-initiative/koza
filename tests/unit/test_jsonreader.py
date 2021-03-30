import gzip
from pathlib import Path

import pytest
from glom import Path as GlomPath

from koza.io.reader.json_reader import JSONReader

test_ddpheno = Path(__file__).parents[1] / 'resources' / 'source-files' / 'ddpheno.json.gz'

glom_path = GlomPath(*['graphs', 0, 'nodes'])


def test_normal_case():
    with gzip.open(test_ddpheno, 'rt') as ddpheno:
        json_reader = JSONReader(ddpheno, glom_path=glom_path)
        row = next(json_reader)
        assert row['id'] == 'http://purl.obolibrary.org/obo/DDPHENO_0001198'


def test_required_properties():
    with gzip.open(test_ddpheno, 'rt') as ddpheno:
        json_reader = JSONReader(ddpheno, ['id'], glom_path=glom_path)
        for row in json_reader:
            assert 'id' in row


def test_missing_req_property_raises_exception():
    with gzip.open(test_ddpheno, 'rt') as ddpheno:
        json_reader = JSONReader(ddpheno, ['fake_prop'], glom_path=glom_path)
        with pytest.raises(ValueError):
            next(json_reader)
