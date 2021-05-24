"""
Testing the biolink model dataclasses + pydandic
"""
from koza.model.biolink.model import MolecularEntity


def test_default_categories():
    """
    Test that categories are inferred from the mro chain
    """
    molec_entity = MolecularEntity()
    assert molec_entity.category == ['NamedThing', 'MolecularEntity']
