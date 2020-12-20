from typing import TextIO
import yaml


class TranslationTable:
    """
    A class that converts a yaml map into
    a frozen dictionary

    TODO consider making this a bidict
    """

    __slots__= ('source_to_global', 'global')

    def __init__(self, src_handle: TextIO, global_handle: TextIO):
        """
        consider just using **kwargs instead
        of requiring a file handle that contains
        valid yaml

        :param yaml_handle:
        """
        source_map = yaml.safe_load(src_handle)

        # check that the source file is a map

        # check that the source file is a bimap

        # load into slots

        # freeze
