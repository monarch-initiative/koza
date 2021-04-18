"""
Testing for row filtering

"""
import pytest

from koza.model.config.source_config import ColumnFilter, FilterCode, FilterInclusion
from koza.row_filter import RowFilter


@pytest.mark.parametrize(
    "column, inclusion, code, value, result",
    [
        ('a', 'include', 'eq', 0.3, True),
        ('a', 'exclude', 'eq', 0.3, False),
        ('a', 'include', 'ge', 0.3, True),
        ('a', 'include', 'le', 0.3, True),
        ('a', 'include', 'ne', 0.3, False),
        ('a', 'include', 'ne', 0.4, True),
        ('a', 'include', 'lt', 0.4, True),
        ('a', 'include', 'gt', 0.4, False),
        ('a', 'include', 'gt', 0.2, True),
        ('a', 'exclude', 'gt', 0.4, True),
        ('a', 'exclude', 'gt', 0.2, False),
        ('b', 'include', 'eq', 10, True),
        ('b', 'include', 'ge', 10, True),
        ('b', 'include', 'le', 10, True),
        ('b', 'include', 'gt', 9, True),
        ('b', 'include', 'gt', 11, False),
        ('b', 'include', 'lt', 11, True),
        ('b', 'include', 'lt', 9, False),
        ('c', 'include', 'eq', 'llama', True),
        ('c', 'include', 'ne', 'alpaca', True),
        ('c', 'include', 'eq', 'alpaca', False),
        ('c', 'include', 'in', ['llama', 'alpaca'], True),
        ('c', 'include', 'in', ['condor', 'alpaca'], False),
    ],
)
def test_filter(column, inclusion, code, value, result):
    row = {'a': 0.3, 'b': 10, 'c': 'llama'}
    column_filter = ColumnFilter(
        column=column,
        inclusion=FilterInclusion(inclusion),
        filter_code=FilterCode(code),
        value=value,
    )

    rf = RowFilter([column_filter])

    assert rf.include_row(row) is result


@pytest.mark.parametrize(
    "column_filters, result",
    [
        (
            [
                ColumnFilter(
                    column='a',
                    inclusion=FilterInclusion('include'),
                    filter_code=FilterCode('lt'),
                    value=0.4,
                ),
                ColumnFilter(
                    column='a',
                    inclusion=FilterInclusion('include'),
                    filter_code=FilterCode('gt'),
                    value=0.1,
                ),
            ],
            True,
        ),
        (
            [
                ColumnFilter(
                    column='a',
                    inclusion=FilterInclusion('include'),
                    filter_code=FilterCode('lt'),
                    value=0.4,
                ),
                ColumnFilter(
                    column='a',
                    inclusion=FilterInclusion('exclude'),
                    filter_code=FilterCode('gt'),
                    value=0.4,
                ),
            ],
            True,
        ),
        (
            [
                ColumnFilter(
                    column='a',
                    inclusion=FilterInclusion('include'),
                    filter_code=FilterCode('in'),
                    value=[0.2, 0.3, 0.4],
                ),
                ColumnFilter(
                    column='b',
                    inclusion=FilterInclusion('exclude'),
                    filter_code=FilterCode('lt'),
                    value=9,
                ),
            ],
            True,
        ),
        (
            [
                ColumnFilter(
                    column='a',
                    inclusion=FilterInclusion('include'),
                    filter_code=FilterCode('in'),
                    value=[0.2, 0.3, 0.4],
                ),
                ColumnFilter(
                    column='b',
                    inclusion=FilterInclusion('exclude'),
                    filter_code=FilterCode('gt'),
                    value=9,
                ),
            ],
            False,
        ),
    ],
)
def test_multiple_filters(column_filters, result):
    row = {'a': 0.3, 'b': 10, 'c': 'llama'}

    rf = RowFilter(column_filters)

    assert rf.include_row(row) == result


def test_empty_filters():
    row = {'a': 0.3, 'b': 10, 'c': 'llama'}

    rf = RowFilter()

    assert rf.include_row(row)
