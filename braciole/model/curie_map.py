from dataclasses import FrozenInstanceError

from ..validator import is_dictionary_bimap


class CurieMap:
    """
    A class that converts a yaml map into
    a frozen dictionary

    TODO consider making this a bidict
    """

    def __init__(self, **curie_map):
        """
        consider just using **kwargs instead
        of requiring a file handle that contains
        valid yaml

        :param yaml_handle:
        """

        if not is_dictionary_bimap(curie_map):
            raise ValueError("Global table is not a bimap")

        self.__dict__.update(curie_map.keys(), **curie_map)

        for prefix, reference in curie_map:
            setattr(prefix, reference)

    def __setattr__(self, key, value):
        raise FrozenInstanceError(f"cannot assign to field {key!r}")

    def __delattr__(self, item):
        raise FrozenInstanceError(f"cannot delete field {item!r}")
