"""
Testing the biolink model dataclasses + pydandic

tests validators and converters
"""

from koza.model.biolink.model import Entity


def test_entity_provided_by_to_list_converter():
    """
    Test that passing a string to Entity.provided_by is converted to a list
    """
    entity = Entity()
    entity.provided_by = 'stringdb'
    assert entity.provided_by == ['stringdb']
