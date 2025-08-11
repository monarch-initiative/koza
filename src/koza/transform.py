from dataclasses import dataclass, field
from typing import Any

from loguru import logger
from typing_extensions import assert_never

from koza.io.writer.writer import KozaWriter
from koza.model.transform import MapErrorEnum
from koza.utils.exceptions import MapItemException

Record = dict[str, Any]
Mappings = dict[str, dict[str, dict[str, str]]]


@dataclass(kw_only=True)
class KozaTransform:
    extra_fields: dict[str, Any]
    writer: KozaWriter
    mappings: Mappings
    on_map_failure: MapErrorEnum = MapErrorEnum.warning
    state: dict[Any, Any] = field(default_factory=dict)

    def write(self, *records: Any, writer: str | None = None) -> None:
        """Write a series of records to a writer.

        The writer argument specifies the specific writer to write to (named
        writers not yet implemented)
        """
        self.writer.write(records)

    def lookup(self, name: str, map_column: str, map_name: str | None = None) -> str:
        """Look up a term in the configured mappings.

        In the one argument form:

            koza.lookup("name")

        It will look for the first match for "name" in the configured mappings.
        The first mapping will have precendence over any proceeding ones.

        If a map name is provided, only that named mapping will be used:

            koza.lookup("name", map_name="mapping_a")

        """
        try:
            if map_name:
                mapping = self.mappings.get(map_name, None)
                if mapping is None:
                    raise MapItemException(f"Map {map_name} does not exist")

                values = mapping.get(name, None)
                if values is None:
                    raise MapItemException(f"No record for {name} in map {map_name}")

                mapped_value = values.get(map_column, None)
                if mapped_value is None:
                    raise MapItemException(f"No record for {name} in column {map_column} in {map_name}")

                return mapped_value
            else:
                for mapping in self.mappings.values():
                    values = mapping.get(name, None)
                    if values is None:
                        raise MapItemException(f"No record for {name} in map {map_name}")

                    mapped_value = values.get(map_column, None)
                    if mapped_value is None:
                        raise MapItemException(f"No record for {name} in column {map_column} in {map_name}")

                    return mapped_value
                else:
                    raise MapItemException(f"No record found in any mapping for {name} in column {map_column}")
        except MapItemException as e:
            match self.on_map_failure:
                case MapErrorEnum.error:
                    raise e
                case MapErrorEnum.warning:
                    return name
                case _:
                    assert_never(self.on_map_failure)

    def log(self, msg: str, level: str = "INFO") -> None:
        """Log a message."""
        logger.log(level, msg)

    @property
    def current_reader(self) -> str:
        """Returns the reader for the last row read.

        Useful for getting the filename of the file that a row was read from:

            for row in koza.iter_rows():
                filename = koza.current_reader.filename
        """
        ...
