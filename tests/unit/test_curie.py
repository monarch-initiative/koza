"""
Testing the biolink model dataclasses + pydandic
"""
import pytest
from pydantic import ValidationError

from koza.model.biolink.named_thing import *


def test_bad_curie():
    """
    a misformatted curie returns a validation error
    """
    entity = Entity()
    with pytest.raises(ValidationError):
        entity.id = "this is not a curie"


def test_bad_curie_in_list():
    """
    Test that misformatted curie in a list returns a validation error
    """
    with pytest.raises(ValidationError):
        pub = Publication(id='PMID:123', mesh_terms=['foo:bar', 'bad_curie'])


def test_good_curie():
    """
    Tests that a properly formatted curie works, and
    that a string is equivalent to the Curie type
    """
    entity = Entity()
    entity.id = 'HP:0000001'
    assert 'HP:0000001' is entity.id  # noqa: F632
    assert 'HP:0000001' == entity.id
