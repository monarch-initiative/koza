import json
import logging
from typing import IO, Any, Dict, Iterator, List

LOG = logging.getLogger(__name__)


class JSONLReader:
    """
    A simple JSON lines reader that optionally returns a subset of
    configured properties
    """

    def __init__(self, io_str: IO[str], properties: List[str] = None):
        """

        :param io_str: Any IO stream that yields a string
                       See https://docs.python.org/3/library/io.html#io.IOBase
        :param properties: property list, used to return a subset of properties
        """
        self.io_str = io_str
        self.properties = properties

    def __iter__(self) -> Iterator:
        return self

    def __next__(self) -> Dict[str, Any]:
        next_line = self.io_str.readline()
        if not next_line:
            raise StopIteration
        json_obj = json.loads(next_line)

        if self.properties:
            if not set(json_obj.keys()) >= set(self.properties):
                raise ValueError(
                    f"Configured properties missing in source file "
                    f"{set(self.properties) - set(json_obj.keys())}"
                )
            json_obj = {key: json_obj[key] for key in json_obj.keys() if key in self.properties}

        return json_obj
