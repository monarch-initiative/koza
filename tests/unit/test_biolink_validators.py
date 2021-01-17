"""
Testing the biolink model dataclasses + pydandic

tests validators and converters
"""
import pytest
from pydantic import ValidationError

from bioweave.model.biolink.named_thing import *
from bioweave.model.biolink.association import *


def test_taxon_validator():
    with pytest.raises(ValidationError):
        molec_entity = MolecularEntity(
            in_taxon=['taxon:foo', 'NCBITaxon:2']
        )


def test_taxon_validator_with_setter():
    with pytest.raises(ValidationError):
        molec_entity = MolecularEntity()
        molec_entity.in_taxon = ['taxon:foo', 'NCBITaxon:2']


def test_assoc_publication_to_scalar_converter():
    assoc = Association()
    assoc.publications = [
        Publication(id='PMID:123'),
        Publication(id='PMID:456')
    ]
    assert assoc.publications == ['PMID:123', 'PMID:456']


def test_assoc_subject_to_scalar_converter():
    assoc = Association()
    assoc.subject = Entity(id='foo:bar')
    assert assoc.subject == 'foo:bar'


def test_entity_provided_by_to_list_converter():
    entity = Entity()
    entity.provided_by = 'stringdb'
    assert entity.provided_by == ['stringdb']
