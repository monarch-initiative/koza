"""
Helper functions for facade files

Goal is to keep this as simple as possible

At a high level we want super simple event driven code

Currently this is implemented with exceptions, but this
assumes that all "events" will trigger the code
to break out of its lexical scope

Some other options described here if this needs to be
more complex: https://stackoverflow.com/a/16192256
"""
from koza.validator.exceptions import NextRowException


def next_row():
    """
    Breaks out of the facade file and iterates to the next row
    in the file

    Effectively a continue statement
    https://docs.python.org/3/reference/simple_stmts.html#continue
    :return:
    """
    raise NextRowException
