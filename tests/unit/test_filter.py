"""
Testing for row filtering

"""
import pytest

from koza.model.config.source_config import Filter, FilterCode, ColumnFilter

from koza.dsl.row_filter import RowFilter


@pytest.mark.parametrize("column, code, value, result",
                         [('a', 'eq', .3, True),
                          ('a', 'gte', .3, True),
                          ('a', 'lte', .3, True),
                          ('a', 'ne', .3, False),
                          ('a', 'ne', .4, True),
                          ('a', 'lt', .4, True),
                          ('a', 'gt', .4, False),
                          ('a', 'gt', .2, True),
                          ('b', 'eq', 10, True),
                          ('b', 'gte', 10, True),
                          ('b', 'lte', 10, True),
                          ('b', 'gt', 9, True),
                          ('b', 'gt', 11, False),
                          ('b', 'lt', 11, True),
                          ('b', 'lt', 9, False),
                          ('c', 'eq', 'llama', True),
                          ('c', 'ne', 'alpaca', True),
                          ('c', 'eq', 'alpaca', False),
                          ('c', 'in', ['llama', 'alpaca'], True),
                          ('c', 'in', ['condor', 'alpaca'], False)
                          ])
def test_filter(column, code, value, result):
    row = {'a': .3, 'b': 10, 'c': 'llama'}
    column_filter = ColumnFilter(column=column, filter=Filter(filter=FilterCode(code), value=value))

    rf = RowFilter([column_filter])

    assert rf.include_row(row) is result
