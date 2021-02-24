"""
Custom exceptions
"""


class NextRowException(Exception):
    """Triggers an iterator to continue to the next row"""


class MapItemException(KeyError):
    """
    Special case of KeyError for source maps based on configuration,
    a source may opt to warn or exit with an error
    """
