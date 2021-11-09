"""
Testing the biolink config dataclasses + pydandic

"""
from pathlib import Path

import pytest
import yaml

from koza.model.config.source_config import PrimaryFileConfig

base_config = Path(__file__).parent / 'resources' / 'primary-source.yaml'


def test_source_primary_config():
    with open(base_config, 'r') as config:
        PrimaryFileConfig(**yaml.safe_load(config))

def test_inline_local_table():
    with open(base_config, 'r') as config:
        config = PrimaryFileConfig(**yaml.safe_load(config))
    assert config.local_table["is just a little to the left of"] == "RO:123"

@pytest.mark.parametrize(
    "inclusion, column, filter_code, value",
    (
        [
            ('include', 'combined_score', 'lt', '70'),
            ('exclude', 'combined_score', 'lt', '70'),
            ('include', 'combined_score', 'in', '70'),
            ('exclude', 'combined_score', 'in', '70'),
            ('exclude', 'combined_score', 'in', 70),
            ('exclude', 'combined_score', 'in', 0.7),
            ('include', 'combined_score', 'eq', ['goat', 'sheep']),
            ('include', 'combined_score', 'lt', ['goat', 'sheep']),
            ('include', 'combined_score', 'gte', ['goat', 'sheep']),
            ('exclude', 'is_ungulate', 'eq', 'T'),
        ]
    ),
)
def test_wrong_filter_type_raises_exception(inclusion, column, filter_code, value):
    """
    Test if include and exclude raise a
    value error when handed an incompatible type,
    eg a string when using the lt operator
    """
    with open(base_config, 'r') as config:
        source_config = yaml.safe_load(config)
        del source_config['filters']

        source_config['filters'] = [
            {'column': column, 'inclusion': inclusion, 'filter_code': filter_code, 'value': value}
        ]
        with pytest.raises(ValueError):
            PrimaryFileConfig(**source_config)


@pytest.mark.parametrize("inclusion, code", [('include', 'lgt'), ('exclude', 'ngte')])
def test_wrong_filter_code_raises_exception(inclusion, code):
    with open(base_config, 'r') as config:
        source_config = yaml.safe_load(config)
        source_config['filters'] = [
            {'column': 'combined_score', 'inclusion': inclusion, 'filter_code': code, 'value': 70}
        ]
        with pytest.raises(ValueError):
            PrimaryFileConfig(**source_config)
