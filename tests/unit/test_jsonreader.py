import gzip
from pathlib import Path

import pytest
from koza.io.reader.json_reader import JSONReader
from koza.model.formats import InputFormat
from koza.model.reader import JSONReaderConfig

test_zfin_data = Path(__file__).parents[1] / "resources" / "source-files" / "test_BGI_ZFIN.json.gz"

json_path = [
    "data",
    0,
]


def test_normal_case():
    config = JSONReaderConfig(
        format=InputFormat.json,
        json_path=json_path,
        files=[],
    )
    with gzip.open(test_zfin_data, "rt") as zfin:
        json_reader = JSONReader(zfin, config)
        row = next(iter(json_reader))
        assert row["symbol"] == "gdnfa"


def test_required_properties():
    config = JSONReaderConfig(
        format=InputFormat.json,
        json_path=json_path,
        required_properties=["name", "basicGeneticEntity.primaryId"],
        files=[],
    )
    with gzip.open(test_zfin_data, "rt") as zfin:
        json_reader = JSONReader(zfin, config)
        for row in json_reader:
            print(row)
            assert row["name"]
            assert row["basicGeneticEntity"]["primaryId"]


def test_missing_req_property_raises_exception():
    config = JSONReaderConfig(
        format=InputFormat.json,
        json_path=json_path,
        required_properties=["fake_prop"],
        files=[],
    )
    with gzip.open(test_zfin_data, "rt") as zfin:
        json_reader = JSONReader(zfin, config)
        with pytest.raises(ValueError):
            next(iter(json_reader))
