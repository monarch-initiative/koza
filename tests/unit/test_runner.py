from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter

import koza
from koza.io.writer.writer import KozaWriter
from koza.model.formats import InputFormat
from koza.model.koza import KozaConfig
from koza.runner import KozaRunner, KozaTransform, KozaTransformHooks
from koza.utils.exceptions import NoTransformException


class MockWriter(KozaWriter):
    def __init__(self):
        self.items = []

    def write(self, entities):
        self.items += entities

    def write_nodes(self, nodes):
        self.items += nodes

    def write_edges(self, edges):
        self.items += edges

    def finalize(self):
        pass


def test_run_single():
    data = [{"a": 1, "b": 2}]
    writer = MockWriter()

    @koza.transform()
    def transform(koza: KozaTransform, data):
        for record in data:
            koza.write(record)

    runner = KozaRunner(
        data=data,
        writer=writer,
        hooks=KozaTransformHooks(transform=[transform]),
    )
    runner.run()

    assert writer.items == [{"a": 1, "b": 2}]


def test_run_serial():
    data = [{"a": 1, "b": 2}]
    writer = MockWriter()

    @koza.transform_record()
    def transform_record(koza: KozaTransform, record: dict[str, Any]):
        koza.write(record)

    runner = KozaRunner(
        data=data,
        writer=writer,
        hooks=KozaTransformHooks(transform_record=[transform_record]),
    )
    runner.run()

    assert writer.items == [{"a": 1, "b": 2}]


def test_prepare_data():
    data = [{"a": 1}, {"b": 2}]
    writer = MockWriter()

    @koza.prepare_data()
    def prepare_data(koza: KozaTransform, data):
        assert data == [{"a": 1}, {"b": 2}]
        for record in data:
            for k, v in record.items():
                yield {k: v + 1}

    @koza.transform_record()
    def transform_record(koza: KozaTransform, record: dict[str, Any]):
        yield record

    runner = KozaRunner(
        data=data,
        writer=writer,
        hooks=KozaTransformHooks(
            prepare_data=[prepare_data],
            transform_record=[transform_record],
        ),
    )
    runner.run()

    assert writer.items == [{"a": 2}, {"b": 3}]


def test_transform_state():
    writer = MockWriter()

    data = [{"a": 1}, {"b": 2}]

    @koza.on_data_begin()
    def on_data_begin(koza: KozaTransform):
        koza.state["count"] = 0

    @koza.on_data_end()
    def on_data_end(koza: KozaTransform):
        koza.write(koza.state)

    @koza.transform_record()
    def transform_record(koza: KozaTransform, record: dict[str, Any]):
        koza.state["count"] += 1

    runner = KozaRunner(
        data=data,
        writer=writer,
        hooks=KozaTransformHooks(
            transform_record=[transform_record],
            on_data_begin=[on_data_begin],
            on_data_end=[on_data_end],
        ),
    )
    runner.run()

    assert writer.items == [{"count": 2}]


def test_post_transform_fn(caplog):
    writer = MockWriter()

    @koza.transform_record()
    def transform_record(koza: KozaTransform, record: dict[str, Any]):
        koza.write(record)

    @koza.on_data_begin()
    def on_data_begin(koza: KozaTransform):
        writer.write(["called at start"])

    @koza.on_data_end()
    def on_data_end(koza: KozaTransform):
        koza.log("logged post transform function")
        writer.write(["called at end"])

    runner = KozaRunner(
        data=[{"my": "data"}],
        writer=writer,
        hooks=KozaTransformHooks(
            transform_record=[transform_record],
            on_data_begin=[on_data_begin],
            on_data_end=[on_data_end],
        ),
    )
    runner.run()

    assert writer.items == ["called at start", {"my": "data"}, "called at end"]
    assert caplog.records[-1].msg == "logged post transform function"


def test_fn_required():
    writer = MockWriter()

    with pytest.raises(NoTransformException):
        runner = KozaRunner(data=[], writer=writer, hooks=KozaTransformHooks())
        runner.run()


def test_exactly_one_fn_required():
    writer = MockWriter()

    @koza.transform()
    def transform(koza: KozaTransform, data):
        for record in data:
            koza.write(record)

    @koza.transform_record()
    def transform_record(koza: KozaTransform, record: dict[str, Any]):
        koza.write(record)

    with pytest.raises(ValueError):
        runner = KozaRunner(
            data=[],
            writer=writer,
            hooks=KozaTransformHooks(
                transform=[transform],
                transform_record=[transform_record],
            ),
        )
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

    runner = KozaRunner.from_config(config, base_directory=Path(__file__).parent.parent.parent)
    hooks = runner.hooks_by_tag[None]
    assert len(hooks.transform) == 1


def test_override_input_files():
    config_file = (Path(__file__).parent / "../../examples/string/protein-links-detailed.yaml").resolve()
    config, runner = KozaRunner.from_config_file(
        str(config_file),
        input_files=[
            "foo.tsv",
            "bar.tsv",
        ],
    )
    readers = config.get_readers()
    assert readers[0].reader.files == ["foo.tsv", "bar.tsv"]
    assert readers[0].reader.format == InputFormat.csv


def test_override_input_file_directory():
    config_file = (Path(__file__).parent / "../../examples/string/protein-links-detailed.yaml").resolve()
    config, runner = KozaRunner.from_config_file(
        str(config_file),
        input_files_dir="/override_input_dir/"
    )
    readers = config.get_readers()
    assert readers[0].reader.files == ["/override_input_dir/../data/string.tsv",
                                       "/override_input_dir/../data/string2.tsv"]
    assert readers[0].reader.format == InputFormat.csv


def test_override_input_files_and_directory():
    config_file = (Path(__file__).parent / "../../examples/string/protein-links-detailed.yaml").resolve()
    config, runner = KozaRunner.from_config_file(
        str(config_file),
        input_files=[
            "foo.tsv",
            "bar.tsv",
        ],
        input_files_dir="/override_input_dir/"
    )
    readers = config.get_readers()
    assert readers[0].reader.files == ["/override_input_dir/foo.tsv",
                                       "/override_input_dir/bar.tsv"]
    assert readers[0].reader.format == InputFormat.csv