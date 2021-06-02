"""
Testing the biolink model dataclasses + pydandic

tests validators and converters
"""
import pytest
from pydantic import ValidationError

from koza.model.biolink.model import Entity, Gene, Publication


def test_entity_provided_by_to_list_converter():
    """
    Test that passing a string to Entity.provided_by is converted to a list
    """
    entity = Entity(id="HP:123")
    entity.provided_by = 'stringdb'
    assert entity.provided_by == ['stringdb']


def test_bad_curie():
    """
    a misformatted curie returns a validation error
    """
    with pytest.raises(ValidationError):
        entity = Entity(id="this is not a curie")


def test_missing_required_field_raises_error():
    """
    test missing required field raises error
    """
    with pytest.raises(ValidationError):
        Entity()


def test_bad_curie_in_list():
    """
    Test that misformatted curie in a list returns a validation error
    """
    with pytest.raises(ValidationError):
        pub = Publication(id='PMID:123', mesh_terms=['foo:bar', 'bad_curie'])


def test_bad_curie_prefix(caplog):
    """
    Test that misformatted curie in a list returns a validation error
    """
    gen_ent = Gene(id='NCBIGene:123', in_taxon='taxon:foo')
    assert caplog.records[0].levelname == 'WARNING'
    assert caplog.records[0].msg.startswith("taxon:foo prefix 'taxon' not in curie map")
    assert caplog.records[1].msg.startswith("Consider one of ['NCBITaxon', 'MESH']")


def test_good_curie():
    """
    Tests that a properly formatted curie works, and
    that a string is equivalent to the Curie type
    """
    entity = Entity(id='HP:0000001')
    assert 'HP:0000001' == entity.id
