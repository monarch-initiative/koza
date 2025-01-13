"""
source config data class
map config data class
"""

from dataclasses import field
from enum import Enum
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from koza.model.config.pydantic_config import PYDANTIC_CONFIG
from koza.model.formats import InputFormat
from pydantic import Discriminator, StrictInt, StrictStr, Tag
from pydantic.dataclasses import dataclass


__all__ = ('ReaderConfig',)

class FieldType(str, Enum):
    """Enum for field types"""

    str = "str"
    int = "int"
    float = "float"


class HeaderMode(str, Enum):
    """Enum for supported header modes in addition to an index based lookup"""

    infer = "infer"
    none = "none"



@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class BaseReaderConfig:
    files: List[str] = field(default_factory=list)


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class CSVReaderConfig(BaseReaderConfig):
    format: Literal[InputFormat.csv] = InputFormat.csv
    columns: Optional[List[Union[str, Dict[str, FieldType]]]] = None
    field_type_map: Optional[dict[str, FieldType]] = None
    delimiter: str = "\t"
    header_delimiter: Optional[str] = None
    dialect: str = "excel"
    header_mode: Union[int, HeaderMode] = HeaderMode.infer
    header_delimiter: Optional[str] = None
    header_prefix: Optional[str] = None
    skip_blank_lines: bool = True
    comment_char: str = "#"

    def __post_init__(self):
        # Format tab as delimiter
        if self.delimiter in ["tab", "\\t"]:
            object.__setattr__(self, "delimiter", "\t")

        # Create a field_type_map if columns are supplied
        if self.columns:
            field_type_map = {}
            for field in self.columns:
                if isinstance(field, str):
                    field_type_map[field] = FieldType.str
                else:
                    if len(field) != 1:
                        raise ValueError("Field type map contains more than one key")
                    for key, val in field.items():
                        field_type_map[key] = val
            object.__setattr__(self, "field_type_map", field_type_map)

        if self.header_mode == HeaderMode.none and not self.columns:
            raise ValueError(
                "there is no header and columns have not been supplied\n"
                "configure the 'columns' field or set header to the 0-based"
                "index in which it appears in the file, or set this value to"
                "'infer'"
            )


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class JSONLReaderConfig(BaseReaderConfig):
    format: Literal[InputFormat.jsonl] = InputFormat.jsonl
    required_properties: Optional[List[str]] = None


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class JSONReaderConfig(BaseReaderConfig):
    format: Literal[InputFormat.json] = InputFormat.json
    required_properties: Optional[List[str]] = None
    json_path: Optional[List[Union[StrictStr, StrictInt]]] = None


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class YAMLReaderConfig(BaseReaderConfig):
    format: Literal[InputFormat.yaml] = InputFormat.yaml
    required_properties: Optional[List[str]] = None
    json_path: Optional[List[Union[StrictStr, StrictInt]]] = None


def get_reader_discriminator(model: Any):
    if isinstance(model, dict):
        return model.get("format", InputFormat.csv)
    return getattr(model, "format", InputFormat.csv)


ReaderConfig = Annotated[
    (
        Annotated[CSVReaderConfig, Tag(InputFormat.csv)]
        | Annotated[JSONLReaderConfig, Tag(InputFormat.jsonl)]
        | Annotated[JSONReaderConfig, Tag(InputFormat.json)]
        | Annotated[YAMLReaderConfig, Tag(InputFormat.yaml)]
    ),
    Discriminator(get_reader_discriminator),
]
