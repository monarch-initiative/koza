from enum import Enum
from typing import Annotated, List, Literal, Union

from pydantic import Field, StrictFloat, StrictInt, StrictStr
from pydantic.dataclasses import dataclass

from koza.model.config.pydantic_config import PYDANTIC_CONFIG

__all__ = ("ColumnFilter",)


class FilterCode(str, Enum):
    """Enum for filter codes (ex. gt = greater than)

    This should be aligned with https://docs.python.org/3/library/operator.html
    """

    gt = "gt"
    ge = "ge"
    lt = "lt"
    lte = "le"
    eq = "eq"
    ne = "ne"
    inlist = "in"
    inlist_exact = "in_exact"


class FilterInclusion(str, Enum):
    """Enum for filter inclusion/exclusion"""

    include = "include"
    exclude = "exclude"


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class BaseColumnFilter:
    column: str
    inclusion: FilterInclusion


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class ComparisonFilter(BaseColumnFilter):
    filter_code: Literal[FilterCode.lt, FilterCode.gt, FilterCode.lte, FilterCode.ge]
    value: Union[StrictInt, StrictFloat]


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class EqualsFilter(BaseColumnFilter):
    filter_code: Literal[FilterCode.eq]
    value: Union[StrictInt, StrictFloat, StrictStr]


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class NotEqualsFilter(BaseColumnFilter):
    filter_code: Literal[FilterCode.ne]
    value: Union[StrictInt, StrictFloat, StrictStr]


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class InListFilter(BaseColumnFilter):
    filter_code: Literal[FilterCode.inlist, FilterCode.inlist_exact]
    value: List[Union[StrictInt, StrictFloat, StrictStr]]


ColumnFilter = Annotated[
    Union[ComparisonFilter, EqualsFilter, NotEqualsFilter, InListFilter],
    Field(..., discriminator="filter_code"),
]
