from operator import eq, ge, gt, le, lt, ne
from typing import Any, Callable

from koza.model.filters import ColumnFilter, FilterInclusion


class RowFilter:
    """
    A Filter class that is initialized with a List of column filters, each specifying a column, an operator and a value
    """

    def __init__(self, filters: list[ColumnFilter] | None = None):
        """
        :param filters: A collection of Filters to be applied
        """
        self.filters = filters
        self.operators: dict[str, Callable[[Any, Any], bool]] = {
            "gt": gt,
            "ge": ge,
            "lt": lt,
            "le": le,
            "eq": eq,
            "ne": ne,
            "in": self.inlist,  # not using operator.contains because the it expects opposite argument order
            "in_exact": self.inlist_exact,  # not using operator.contains because the it expects opposite argument order
        }

    def include_row(self, row: dict[str, Any]) -> bool:
        """
        :param row: A dictionary representing a single row
        :return: bool for whether the row should be included
        """

        if not self.filters:
            return True

        for column_filter in self.filters:
            row_value = row.get(column_filter.column)

            # None can't be greater, less than or equal to any specified value, right?
            if row_value is None:
                return False

            include = column_filter.inclusion == FilterInclusion("include")
            exclude = column_filter.inclusion == FilterInclusion("exclude")

            comparison_method = self.operators.get(column_filter.filter_code)
            if comparison_method is None:
                raise ValueError("No such operator for filter code `{column_filter.filter_code}`")

            comparison_match = comparison_method(row_value, column_filter.value)

            if (include and not comparison_match) or (exclude and comparison_match):
                return False

        return True

    def inlist(self, column_value: Any, filter_values: list[str]):
        # Check if the passed in column is exactly matched against
        # For a filter_list of ['abc','def','ghi']; this will be true
        # for column_value 'abc' but not 'abcde.'
        if column_value in filter_values:
            return True

        if not isinstance(column_value, str):
            return False

        # The following iterates through all filters and will return true if
        # the text of the  filter is found within the column_value.
        # So for the above example this boolean will return True, because :'abc' in 'abcde': returns True.
        for filter_value in filter_values:
            if filter_value in column_value:
                return True

        return False

    def inlist_exact(self, column_value, filter_values):
        # Check if the passed in column is exactly matched against
        # For a filter_list of ['abc','def','ghi']; this will be true
        # for column_value 'abc' but not 'abcde.'
        if column_value in filter_values:
            return True
