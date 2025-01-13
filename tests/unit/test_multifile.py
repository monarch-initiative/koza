from koza.model.source import Source
from koza.runner import KozaRunner


def test_source_with_multiple_files():
    source_file = f"examples/string/protein-links-detailed.yaml"
    config, runner = KozaRunner.from_config_file(source_file)

    assert len(config.reader.files) == 2

    source = Source(config)
    row_count = len(list(source))

    assert row_count == 15
