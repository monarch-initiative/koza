"""
Functions that collect biolink model objects and write them
"""

from ..koza_runner import get_koza_app


def write(source_name, *args):
    koza = get_koza_app()
    koza.write(source_name, list(args))
