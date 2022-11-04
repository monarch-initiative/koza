import json
import logging
from typing import IO, Any, Dict, Iterator, List
from koza.io.utils import check_data

LOG = logging.getLogger(__name__)


class JSONLReader:
    """
    A simple JSON lines reader that optionally returns a subset of
    configured properties
    """

    def __init__(
        self,
        io_str: IO[str],
        required_properties: List[str] = None,
        name: str = 'jsonl file',
        row_limit: int = None,
    ):
        """
        :param io_str: Any IO stream that yields a string
                       See https://docs.python.org/3/library/io.html#io.IOBase
        :param required_properties: List of required top level properties
        :param name: todo
        """
        self.io_str = io_str
        self.required_properties = required_properties
        self.line_num = 0
        self.name = name
        self.line_limit = row_limit

    def __iter__(self) -> Iterator:
        return self

    def __next__(self) -> Dict[str, Any]:
        next_line = self.io_str.readline()
        if not next_line:
            LOG.info(f"Finished processing {self.line_num} lines for {self.name} from {self.io_str.name}")
            raise StopIteration
        self.line_num += 1
        if self.line_limit:
            if self.line_num == self.line_limit:
                raise StopIteration

        json_obj = json.loads(next_line)

        # Check that required properties exist in row
        if self.required_properties:
            properties = []
            for prop in self.required_properties:
                new_prop = check_data(json_obj, prop)
                properties.append(new_prop)

            if False in properties:
                raise ValueError(
                    f"Required properties defined for {self.name} are missing from {self.io_str.name}\n"
                    f"Missing properties: {set(self.required_properties) - set(json_obj.keys())}\n"
                    f"Row: {json_obj}"
                )

        return json_obj
