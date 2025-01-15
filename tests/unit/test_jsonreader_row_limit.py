import gzip
from pathlib import Path

import pytest

from koza.io.reader.json_reader import JSONReader
from koza.model.formats import InputFormat
from koza.model.reader import JSONReaderConfig

test_ddpheno = Path(__file__).parents[1] / "resources" / "source-files" / "ddpheno.json.gz"

json_path = ["graphs", 0, "nodes"]


def test_normal_case():
    config = JSONReaderConfig(
        format=InputFormat.json,
        json_path=json_path,
        files=[],
    )
    with gzip.open(test_ddpheno, "rt") as ddpheno:
        json_reader = JSONReader(ddpheno, config=config, row_limit=3)
        row = next(iter(json_reader))
        assert row["id"] == "http://purl.obolibrary.org/obo/DDPHENO_0001198"


def test_required_properties():
    config = JSONReaderConfig(
        format=InputFormat.json,
        required_properties=["id"],
        json_path=json_path,
        files=[],
    )
    with gzip.open(test_ddpheno, "rt") as ddpheno:
        row_limit = 3
        row_count = 0
        json_reader = JSONReader(ddpheno, config=config, row_limit=row_limit)
        for row in json_reader:
            row_count += 1
            assert "id" in row
        assert row_count == row_limit


def test_missing_req_property_raises_exception():
    config = JSONReaderConfig(
        format=InputFormat.json,
        required_properties=["fake_prop"],
        json_path=json_path,
        files=[],
    )
    with gzip.open(test_ddpheno, "rt") as ddpheno:
        json_reader = JSONReader(ddpheno, config, row_limit=3)
        with pytest.raises(ValueError):
            next(iter(json_reader))
