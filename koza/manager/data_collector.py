"""
Functions that collect biolink model objects and write them
"""

from ..koza_runner import get_koza_app


def collect(*args):
    koza = get_koza_app()
    koza.write(*args)
