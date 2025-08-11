from dataclasses import field, fields
from enum import Enum
from typing import Any

from pydantic import model_validator
from pydantic.dataclasses import dataclass
from pydantic_core import ArgsKwargs

from koza.model.config.pydantic_config import PYDANTIC_CONFIG


class MapErrorEnum(str, Enum):
    """Enum for how to handle key errors in map files"""

    warning = "warning"
    error = "error"


@dataclass(config=PYDANTIC_CONFIG, frozen=True, kw_only=True)
class TransformConfig:
    """
    Source config data class

    Parameters
    ----------
    name: name of the source
    code: path to a python file to transform the data
    mode: how to process the transform file
    global_table: path to a global table file
    local_table: path to a local table file
    """

    code: str | None = None
    module: str | None = None
    global_table: str | dict | None = None
    local_table: str | dict | None = None
    mappings: list[str] = field(default_factory=list)
    on_map_failure: MapErrorEnum = MapErrorEnum.warning
    extra_fields: dict[str, Any] = field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def extract_extra_fields(cls, values: dict | ArgsKwargs) -> dict[str, Any]:
        """Take any additional kwargs and put them in the `extra_fields` attribute."""
        if isinstance(values, dict):
            kwargs = values.copy()
        elif isinstance(values, ArgsKwargs) and values.kwargs is not None:
            kwargs = values.kwargs.copy()
        else:
            kwargs = {}

        configured_field_names = {f.name for f in fields(cls) if f.name != "extra_fields"}
        extra_fields: dict[str, Any] = kwargs.pop("extra_fields", {})

        for field_name in list(kwargs.keys()):
            if field_name in configured_field_names:
                continue
            extra_fields[field_name] = kwargs.pop(field_name)
        kwargs["extra_fields"] = extra_fields

        return kwargs
