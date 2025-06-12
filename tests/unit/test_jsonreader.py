import gzip
from pathlib import Path

import pytest

from koza.io.reader.json_reader import JSONReader
from koza.model.reader import JSONReaderConfig

test_zfin_data = Path(__file__).parents[1] / "resources" / "source-files" / "test_BGI_ZFIN.json.gz"

json_path = [
    "data",
    0,
]


def test_normal_case():
    config = JSONReaderConfig(json_path=json_path)
    with gzip.open(test_zfin_data, "rt") as zfin:
        json_reader = JSONReader(zfin, config)
        row = next(iter(json_reader))
        assert row["symbol"] == "gdnfa"


def test_required_property_present():
    config = JSONReaderConfig(
        json_path=json_path,
        required_properties=["name", "basicGeneticEntity.primaryId"],
    )
    with gzip.open(test_zfin_data, "rt") as zfin:
        json_reader = JSONReader(zfin, config)
        for row in json_reader:
            assert "name" in row
            assert "basicGeneticEntity" in row
            assert "primaryId" in row["basicGeneticEntity"]


def test_required_property_missing():
    config = JSONReaderConfig(
        json_path=json_path,
        required_properties=["missing_property"],
    )
    with gzip.open(test_zfin_data, "rt") as zfin:
        json_reader = JSONReader(zfin, config)
        with pytest.raises(ValueError):
            next(iter(json_reader))
