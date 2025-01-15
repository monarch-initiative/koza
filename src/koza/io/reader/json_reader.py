import json
from typing import IO, Any, Dict, Generator, List, Union

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
        config: Union[JSONReaderConfig, YAMLReaderConfig],
        row_limit: int = 0,
    ):
        """
        :param io_str: Any IO stream that yields a string
                       See https://docs.python.org/3/library/io.html#io.IOBase
        :param config: The JSON or YAML reader configuration
        :param row_limit: The number of lines to be read. No limit if 0.
        """
        self.io_str = io_str
        self.config = config
        self.row_limit = row_limit

        if isinstance(config, YAMLReaderConfig):
            json_obj = yaml.safe_load(self.io_str)
        else:
            json_obj = json.load(self.io_str)

        if config.json_path:
            for path in config.json_path:
                json_obj = json_obj[path]

        if isinstance(json_obj, list):
            self.json_obj: List[Any] = json_obj
        else:
            self.json_obj = [json_obj]

    def __iter__(self) -> Generator[Dict[str, Any], None, None]:
        for i, item in enumerate(self.json_obj):
            if self.row_limit and i >= self.row_limit:
                return

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
