from koza.exceptions import MapItemException


class MapDict(dict):
    """
    A custom dictionary that raises a special KeyError exception
    MapItemException
    """

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError as key_error:
            raise MapItemException(*key_error.args)
