import json
import logging
from typing import IO, Any, Dict, Iterator, List

LOG = logging.getLogger(__name__)


class JSONLReader:
    """
    A simple JSON lines reader that optionally returns a subset of
    configured properties
    """

    def __init__(
        self, io_str: IO[str], 
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
            LOG.info(f"Finished processing {self.line_num} lines")
            raise StopIteration
        self.line_num += 1
        if self.line_limit:
            if self.line_num == self.line_limit:
                raise StopIteration
                
        json_obj = json.loads(next_line)

        if self.required_properties:
            if not set(json_obj.keys()) >= set(self.required_properties):
                # TODO - have koza runner handle this exception
                # based on some configuration? similar to
                # on_map_error
                raise ValueError(
                    f"Configured properties missing in source file "
                    f"{set(self.required_properties) - set(json_obj.keys())}"
                )
            # If we want to turn this into a subsetter
            # json_obj = {key: json_obj[key] for key in json_obj.keys() if key in self.required_properties}

        return json_obj
