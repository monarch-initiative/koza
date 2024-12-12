import gzip
from pathlib import Path

import pytest

from koza.io.reader.jsonl_reader import JSONLReader
from koza.model.config.source_config import JSONLReaderConfig, FormatType

test_zfin_data = Path(__file__).parents[1] / 'resources' / 'source-files' / 'ZFIN_PHENOTYPE_0.jsonl.gz'


def test_normal_case():
    config = JSONLReaderConfig(
        format=FormatType.jsonl,
        files=[],
    )
    with gzip.open(test_zfin_data, 'rt') as zfin:
        jsonl_reader = JSONLReader(zfin, config)
        row = next(iter(jsonl_reader))
        assert len(row) == 6

        assert row['objectId'] == 'ZFIN:ZDB-GENE-011026-1'


def test_required_property():
    config = JSONLReaderConfig(
        format=FormatType.jsonl,
        required_properties=["objectId", "evidence.publicationId"],
        files=[],
    )
    with gzip.open(test_zfin_data, 'rt') as zfin:
        jsonl_reader = JSONLReader(zfin, config)
        for row in jsonl_reader:
            # assert len(row) == 1  # removed subsetter
            print(row)
            assert 'objectId' in row
            assert row['evidence']['publicationId']


def test_missing_req_property_raises_exception():
    config = JSONLReaderConfig(
        format=FormatType.jsonl,
        required_properties=["objectId", "foobar"],
        files=[],
    )
    with gzip.open(test_zfin_data, 'rt') as zfin:
        jsonl_reader = JSONLReader(zfin, config)
        with pytest.raises(ValueError):
            next(iter(jsonl_reader))
