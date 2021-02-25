"""
Testing the biolink config dataclasses + pydandic

"""
from pathlib import Path

import pytest
import yaml

from koza.model.config.source_config import PrimarySourceConfig

base_config = Path(__file__).parent / 'resources' / 'primary-source.yaml'


def test_source_primary_config():
    with open(base_config, 'r') as config:
        PrimarySourceConfig(**yaml.safe_load(config))


def test_wrong_filter_type_raises_exception():
    """
    Test if filter_in and filter_out raises a
    value error when handed an incompatible type,
    eg a string when using the lt operator
    """
    with open(base_config, 'r') as config:
        source_config = yaml.safe_load(config)
        source_config['filter_out'][0]['combined_score']['value'] = '70'
        with pytest.raises(ValueError):
            PrimarySourceConfig(**source_config)

        del source_config['filter_out']
        source_config['filter_in'] = [{'combined_score': {'filter': 'lt', 'value': '70'}}]
        with pytest.raises(ValueError):
            PrimarySourceConfig(**source_config)
