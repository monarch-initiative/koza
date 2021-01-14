"""
Helper functions for facade files

Goal is to keep this as simple as possible
"""


class NextRowException(Exception):
    """Triggers an iterator to continue to the next row"""
    pass


def next_row():
    """
    Breaks out of the facade file and iterates to the next row
    in the file

    Effectively a continue statement
    https://docs.python.org/3/reference/simple_stmts.html#continue
    :return:
    """
    raise NextRowException
