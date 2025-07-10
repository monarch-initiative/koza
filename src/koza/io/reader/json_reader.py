import json
from collections.abc import Generator
from typing import IO, Any

import yaml

from koza.io.utils import check_data
from koza.model.reader import JSONReaderConfig, YAMLReaderConfig

# FIXME: Add back logging as part of progress


class JSONReader:
    """
    A JSON reader that optionally iterates over a json list
    """

    def __init__(
        self,
        io_str: IO[str],
        config: JSONReaderConfig | YAMLReaderConfig,
    ):
        """
        :param io_str: Any IO stream that yields a string
                       See https://docs.python.org/3/library/io.html#io.IOBase
        :param config: The JSON or YAML reader configuration
        """
        self.io_str = io_str
        self.config = config

        if isinstance(config, YAMLReaderConfig):
            json_obj = yaml.safe_load(self.io_str)
        else:
            json_obj = json.load(self.io_str)

        if config.json_path:
            for path in config.json_path:
                json_obj = json_obj[path]

        if isinstance(json_obj, list):
            self.json_obj: list[Any] = json_obj
        else:
            self.json_obj = [json_obj]

    def __iter__(self) -> Generator[dict[str, Any], None, None]:
        for item in self.json_obj:
            if not isinstance(item, dict):
                raise ValueError()

            if self.config.required_properties:
                missing_properties = [prop for prop in self.config.required_properties if not check_data(item, prop)]

                if missing_properties:
                    raise ValueError(
                        f"Required properties are missing from {self.io_str.name}\n"
                        f"Missing properties: {missing_properties}\n"
                        f"Row: {item}"
                    )

            yield item
