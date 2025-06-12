import gzip
from pathlib import Path

import pytest

from koza.io.reader.jsonl_reader import JSONLReader
from koza.model.reader import JSONLReaderConfig

test_zfin = Path(__file__).parent.parent / "resources" / "source-files" / "ZFIN_PHENOTYPE_0.jsonl.gz"


def test_normal_case():
    config = JSONLReaderConfig()
    with gzip.open(test_zfin, "rt") as zfin:
        jsonl_reader = JSONLReader(zfin, config)
        row = next(iter(jsonl_reader))
        assert len(row) == 6
        assert row["objectId"] == "ZFIN:ZDB-GENE-011026-1"


def test_required_property_present():
    config = JSONLReaderConfig(
        required_properties=["objectId"],
    )

    with gzip.open(test_zfin, "rt") as zfin:
        jsonl_reader = JSONLReader(zfin, config)
        for row in jsonl_reader:
            assert "objectId" in row
            assert "evidence" in row
            assert "publicationId" in row["evidence"]


def test_required_property_missing():
    config = JSONLReaderConfig(
        required_properties=["objectId", "missing_property"],
    )

    with gzip.open(test_zfin, "rt") as zfin:
        jsonl_reader = JSONLReader(zfin, config)
        with pytest.raises(ValueError):
            next(iter(jsonl_reader))
