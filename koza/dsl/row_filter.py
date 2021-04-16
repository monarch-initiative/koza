from operator import eq, ge, gt, le, lt, ne
from typing import List

from koza.model.config.source_config import ColumnFilter, FilterInclusion


class RowFilter:
    """
    A Filter class that is initialized with a List of column filters, each specifying a column, an operator and a value
    """

    def __init__(self, filters: List[ColumnFilter] = None):
        """
        :param filters: A collection of Filters to be applied
        """
        self.filters = filters
        self.operators = {
            'gt': gt,
            'ge': ge,
            'lt': lt,
            'le': le,
            'eq': eq,
            'ne': ne,
            'in': self.inlist,  # not using operator.contains because the it expects opposite argument order
        }

    def include_row(self, row) -> bool:
        """
        :param row: A dictionary representing a single row
        :return: bool for whether the row should be included
        """

        if not self.filters:
            return True

        include_row = True

        column_filter: ColumnFilter
        for column_filter in self.filters:
            # None can't be greater, less than or equal to any specified value, right?
            if row.get(column_filter.column) is None:
                return False

            include = column_filter.inclusion == FilterInclusion('include')
            exclude = column_filter.inclusion == FilterInclusion('exclude')

            comparison_method = self.operators.get(column_filter.filter_code)
            comparison_match = comparison_method(row.get(column_filter.column), column_filter.value)

            if (include and not comparison_match) or (exclude and comparison_match):
                include_row = False

        return include_row

    def inlist(self, column_value, filter_value):
        return column_value in filter_value
