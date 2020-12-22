from typing import TextIO
import yaml


class CurieMap:
    """
    A class that converts a yaml map into
    a frozen dictionary

    TODO consider making this a bidict
    """

    def __init__(self, yaml_handle: TextIO):
        """
        consider just using **kwargs instead
        of requiring a file handle that contains
        valid yaml

        :param yaml_handle:
        """
        curie_map = yaml.safe_load(yaml_handle)

        # check that the file is a map

        # check that the file is a bimap

        # load into items

        # freeze



