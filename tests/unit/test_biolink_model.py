"""
Testing the biolink model dataclasses + pydandic
"""
from koza.model.biolink.model import MolecularEntity


def test_default_categories():
    """
    Test that categories are inferred from the mro chain
    """
    molec_entity = MolecularEntity(id='HP:123', type='SO:123')
    assert set(molec_entity.category) == set(['biolink:NamedThing', 'biolink:MolecularEntity'])
