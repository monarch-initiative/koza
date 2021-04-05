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


@pytest.mark.parametrize("filter_mode, column, filter_code, value",
                         ([
                             ('filter_in', 'combined_score', 'lt', '70'),
                             ('filter_out', 'combined_score', 'lt', '70'),
                             ('filter_in', 'combined_score', 'in', '70'),
                             ('filter_out', 'combined_score', 'in', '70'),
                             ('filter_out', 'combined_score', 'in', 70),
                             ('filter_out', 'combined_score', 'in', .7),
                             ('filter_in', 'combined_score', 'eq', ['goat', 'sheep']),
                             ('filter_in', 'combined_score', 'lt', ['goat', 'sheep']),
                             ('filter_in', 'combined_score', 'gte', ['goat', 'sheep']),
                             ('filter_out', 'is_ungulate', 'eq', 'T'),
                         ]))
def test_wrong_filter_type_raises_exception(filter_mode, column, filter_code, value):
    """
    Test if filter_in and filter_out raises a
    value error when handed an incompatible type,
    eg a string when using the lt operator
    """
    with open(base_config, 'r') as config:
        source_config = yaml.safe_load(config)
        del source_config['filter_out']

        source_config[filter_mode] = [{column: {'filter': filter_code, 'value': value}}]
        with pytest.raises(ValueError):
            PrimarySourceConfig(**source_config)


@pytest.mark.parametrize("filter_set, code", [('filter_in', 'lgt'),
                                              ('filter_out', 'ngte')])
def test_wrong_filter_code_raises_exception(filter_set, code):
    with open(base_config, 'r') as config:
        source_config = yaml.safe_load(config)
        source_config[filter_set] = [{'combined_score': {'filter': code, 'value': 70}}]
        with pytest.raises(ValueError):
            PrimarySourceConfig(**source_config)

