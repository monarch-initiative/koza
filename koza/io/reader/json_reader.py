import json
import logging
from typing import IO, Any, Dict, Iterator, List

from glom import Path

LOG = logging.getLogger(__name__)


class JSONReader:
    """
    A JSON reader that optionally iterates over a json list
    """

    def __init__(
        self,
        io_str: IO[str],
        required_properties: List[str] = None,
        glom_path: Path = None,
        name: str = 'json file',
    ):
        """
        :param io_str: Any IO stream that yields a string
                       See https://docs.python.org/3/library/io.html#io.IOBase
        :param required_properties: required top level properties
        :param iterate_over: todo
        :param name: todo
        """
        self.io_str = io_str
        self.glom_path = glom_path
        self.required_properties = required_properties
        self.name = name
        self.json_obj = json.load(self.io_str)
        self.iter_json = []

        self._len = len(self.iter_json)
        self._line_num = 0

    def __iter__(self) -> Iterator:
        return self

    def __next__(self) -> Dict[str, Any]:
        # Read the whole json file into memory
        next_obj = self.iter_json[self._line_num]

        if self._line_num > self._len:
            LOG.info(f"Finished processing json file")
            raise StopIteration

        if self.required_properties:
            if not set(next_obj.keys()) >= set(self.required_properties):
                # TODO - have koza runner handle this exception
                # based on some configuration? similar to
                # on_map_error
                raise ValueError(
                    f"Configured properties missing in source file "
                    f"{set(self.required_properties) - set(next_obj.keys())}"
                )

            # If we want to subset
            # next_obj = {key: next_obj[key] for key in next_obj.keys() if key in self.required_properties}

        return next_obj
