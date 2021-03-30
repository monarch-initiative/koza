from pathlib import Path

import pytest
from yaml.constructor import ConstructorError

from koza.curie_util import CurieFileFormat, get_curie_map

curie_yaml = Path(__file__).parent / 'resources' / 'curie_map.yaml'
curie_key_dupe = Path(__file__).parent / 'resources' / 'curie_dupe_key.yaml'
curie_value_dupe = Path(__file__).parent / 'resources' / 'curie_dupe_value.yaml'
curie_jsonld = Path(__file__).parent / 'resources' / 'context.jsonld'


def test_yaml():
    curie_map = get_curie_map(curie_yaml, CurieFileFormat.yaml)
    assert 'rdf' in curie_map
    assert curie_map['rdf'] == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'


def test_yaml_wth_dupe_keys_raises_constructor_error():
    with pytest.raises(ConstructorError):
        get_curie_map(curie_key_dupe, CurieFileFormat.yaml)


def test_yaml_wth_dupe_values_raises_value_error():
    with pytest.raises(ValueError):
        get_curie_map(curie_value_dupe, CurieFileFormat.yaml)


def test_jsonld():
    curie_map = get_curie_map(curie_jsonld, CurieFileFormat.jsonld)
    assert 'APO' in curie_map
    assert curie_map['APO'] == 'http://purl.obolibrary.org/obo/APO_'


def test_default_fetches_biolink():
    """
    This is brittle
    """
    curie_map = get_curie_map(None)
    assert 'biolink' in curie_map
    assert curie_map['biolink'] == 'https://w3id.org/biolink/vocab/'
