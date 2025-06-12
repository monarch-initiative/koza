from typing import Any

import pytest
from pydantic import TypeAdapter

from koza.io.writer.writer import KozaWriter
from koza.model.koza import KozaConfig
from koza.runner import KozaRunner, KozaTransform
from koza.utils.exceptions import NoTransformException


class MockWriter(KozaWriter):
    def __init__(self):
        self.items = []

    def write(self, entities):
        self.items += entities

    def finalize(self):
        pass


def test_run_single():
    data = iter([{"a": 1, "b": 2}])
    writer = MockWriter()

    def transform(koza: KozaTransform):
        for record in koza.data:
            koza.write(record)

    runner = KozaRunner(data=data, writer=writer, transform=transform)
    runner.run()

    assert writer.items == [{"a": 1, "b": 2}]


def test_run_serial():
    data = iter([{"a": 1, "b": 2}])
    writer = MockWriter()

    def transform_record(koza: KozaTransform, record: dict[str, Any]):
        koza.write(record)

    runner = KozaRunner(data=data, writer=writer, transform_record=transform_record)
    runner.run()

    assert writer.items == [{"a": 1, "b": 2}]


def test_fn_required():
    data = iter([])
    writer = MockWriter()

    with pytest.raises(NoTransformException):
        runner = KozaRunner(data=data, writer=writer)
        runner.run()


def test_exactly_one_fn_required():
    data = iter([])
    writer = MockWriter()

    def transform(koza: KozaTransform):
        for record in koza.data:
            koza.write(record)

    def transform_record(koza: KozaTransform, record: dict[str, Any]):
        koza.write(record)

    with pytest.raises(ValueError):
        runner = KozaRunner(data=data, writer=writer, transform=transform, transform_record=transform_record)
        runner.run()


def test_load_config():
    config = TypeAdapter(KozaConfig).validate_python(
        {
            "name": "my-transform",
            "reader": {
                "format": "csv",
                "files": [],
            },
            "transform": {"code": "examples/minimal.py"},
            "writer": {},
        }
    )

    runner = KozaRunner.from_config(config)
    assert callable(runner.transform)
    assert runner.transform_record is None
    assert callable(runner.run)
