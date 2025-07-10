from koza.model.source import Source
from koza.runner import KozaRunner


def test_multiple_file_source():
    config_file = f"examples/string/protein-links-detailed.yaml"
    config, runner = KozaRunner.from_config_file(config_file)

    assert len(config.reader.files) == 2

    source = Source(config)
    row_count = len(list(source))

    assert row_count == 15


def test_multiple_file_row_limit():
    config_file = f"examples/string/protein-links-detailed.yaml"
    config, runner = KozaRunner.from_config_file(config_file)

    assert len(config.reader.files) == 2

    source = Source(config, row_limit=2)
    row_count = len(list(source))

    assert row_count == 2
