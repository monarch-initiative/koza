import json
from typing import IO

from koza.io.utils import check_data
from koza.model.reader import JSONLReaderConfig

# FIXME: Add back logging as part of progress


class JSONLReader:
    """
    A simple JSON lines reader that optionally returns a subset of
    configured properties
    """

    def __init__(
        self,
        io_str: IO[str],
        config: JSONLReaderConfig,
        row_limit: int = 0,
    ):
        """
        :param io_str: Any IO stream that yields a string
                       See https://docs.python.org/3/library/io.html#io.IOBase
        :param config: The JSONL reader configuration
        :param row_limit: The number of lines to be read. No limit if 0.
        """
        self.io_str = io_str
        self.config = config
        self.row_limit = row_limit

    def __iter__(self):
        for i, line in enumerate(self.io_str):
            if self.row_limit and self.row_limit >= i:
                return

            item = json.loads(line)
            if self.config.required_properties:
                missing_properties = [prop for prop in self.config.required_properties if not check_data(item, prop)]

                if missing_properties:
                    raise ValueError(
                        f"Required properties are missing from {self.io_str.name}\n"
                        f"Missing properties: {missing_properties}\n"
                        f"Row: {item}"
                    )

            yield item
