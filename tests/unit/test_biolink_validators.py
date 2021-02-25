"""
Testing the biolink model dataclasses + pydandic

tests validators and converters
"""
import pytest
from pydantic import ValidationError

from koza.model.biolink.association import *
from koza.model.biolink.named_thing import *


def test_taxon_validator():
    """
    Test that passing 'taxon:foo' as a taxon fails, because only
    NCBITaxon is a valid curie prefix for taxa
    """
    with pytest.raises(ValidationError):
        molec_entity = MolecularEntity(in_taxon=['taxon:foo', 'NCBITaxon:2'])


def test_taxon_validator_with_setter():
    """
    Test that validation occurs when using a setter

    This test might be unecesarry and basically proves
    that pydantic validates setters as well as when initializing objects
    which is why we're using it over plain dataclasses
    """
    with pytest.raises(ValidationError):
        molec_entity = MolecularEntity()
        molec_entity.in_taxon = ['taxon:foo', 'NCBITaxon:2']


def test_assoc_publication_to_scalar_converter():
    """
    Test that a list of Publication objects is converted
    to a list of strings
    """
    assoc = Association()
    assoc.publications = [Publication(id='PMID:123'), Publication(id='PMID:456')]
    assert assoc.publications == ['PMID:123', 'PMID:456']


def test_assoc_subject_to_scalar_converter():
    """
    Test that an Entity object is converted to a string
    """
    assoc = Association()
    assoc.subject = Entity(id='foo:bar')
    assert assoc.subject == 'foo:bar'


def test_entity_provided_by_to_list_converter():
    """
    Test that passing a string to Entity.provided_by is converted to a list
    """
    entity = Entity()
    entity.provided_by = 'stringdb'
    assert entity.provided_by == ['stringdb']
