"""
Testing custom dictionary
"""
import pytest

from bioweave.model.map_dict import MapDict
from bioweave.validator.exceptions import MapItemException


def test_custom_dict_exception():
    map_dict = MapDict(foo='bar')
    with pytest.raises(MapItemException):
        bad_item = map_dict['bad_key']


def test_custom_dict_get_item():
    map_dict = MapDict(foo='bar')
    assert map_dict['foo'] == 'bar'
