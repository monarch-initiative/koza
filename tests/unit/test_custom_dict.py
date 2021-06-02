"""
Testing custom dictionary
"""
import pytest

from koza.exceptions import MapItemException
from koza.model.map_dict import MapDict


def test_custom_dict_exception():
    map_dict = MapDict(foo='bar')
    with pytest.raises(MapItemException):
        map_dict['bad_key']


def test_custom_dict_get_item():
    map_dict = MapDict(foo='bar')
    assert map_dict['foo'] == 'bar'
