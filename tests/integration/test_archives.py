import os
from pathlib import Path

import yaml

from koza.io.yaml_loader import UniqueIncludeLoader
from koza.model.config.source_config import PrimaryFileConfig


def test_archive_targz():
    source = Path('tests/resources/string.yaml')
    unzipped_data = Path('tests/resources/source-files/string.tsv.gz')
    # Delete unzipped archive if it exists
    if os.path.exists(unzipped_data.absolute()):
        os.remove(unzipped_data.absolute())

    # Create a SourceConfig object with test config
    with open(source.absolute(), 'r') as src:
        source_config = PrimaryFileConfig(**yaml.load(src, Loader=UniqueIncludeLoader))

    # This method only happens after validation - force it now
    source_config.__post_init_post_parse__()

    assert os.path.exists(unzipped_data)


# test_archive_targz()
