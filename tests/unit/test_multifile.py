from pathlib import Path

from koza.model.source import Source
from koza.runner import KozaRunner

ROOT_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = ROOT_DIR / "tests/output"


def test_multiple_file_source():
    config_file = ROOT_DIR / "examples/string/protein-links-detailed.yaml"
    config, _ = KozaRunner.from_config_file(str(config_file), output_dir=str(OUTPUT_DIR))
    reader_config = config.get_readers()[0].reader

    assert len(reader_config.files) == 2

    source = Source(reader_config, base_directory=Path(config_file).parent)
    row_count = len(list(source))

    assert row_count == 15


def test_multiple_file_row_limit():
    config_file = ROOT_DIR / "examples/string/protein-links-detailed.yaml"
    config, _ = KozaRunner.from_config_file(str(config_file), output_dir=str(OUTPUT_DIR))
    reader_config = config.get_readers()[0].reader

    assert len(reader_config.files) == 2

    source = Source(reader_config, base_directory=Path(config_file).parent, row_limit=2)
    row_count = len(list(source))

    assert row_count == 2
