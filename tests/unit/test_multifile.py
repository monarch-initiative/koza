import pytest
import yaml
from pathlib import Path

from koza.model.source import Source
from koza.model.config.source_config import PrimaryFileConfig
from koza.io.yaml_loader import UniqueIncludeLoader

def test_multiple_files():
    source_file = Path(__file__).parent.parent / 'resources' / 'multifile.yaml'

    row_limit = None
    with open(source_file, 'r') as source_fh:
        source_config = PrimaryFileConfig(**yaml.load(source_fh, Loader=UniqueIncludeLoader))
        if not source_config.name:
            source_config.name = Path(source_file).stem

    source = Source(source_config, row_limit)

    row_count = sum(1 for row in source)

    assert row_count == 15
