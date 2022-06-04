import json, yaml
import logging
from typing import IO, Any, Dict, Iterator, List, Union
#from xmlrpc.client import Boolean

from koza.io.utils import check_data

LOG = logging.getLogger(__name__)

class JSONReader:
    """
    A JSON reader that optionally iterates over a json list
    """

    def __init__(
        self,
        io_str: IO[str],
        required_properties: List[str] = None,
        json_path: List[Union[str, int]] = None,
        name: str = 'json file',
        is_yaml: bool = False,
        row_limit: int = None,
    ):
        """
        :param io_str: Any IO stream that yields a string
                       See https://docs.python.org/3/library/io.html#io.IOBase
        :param required_properties: required top level properties
        :param row_limit: integer number of non-header rows to process
        :param iterate_over: todo
        :param name: todo
        """
        self.io_str = io_str
        self.required_properties = required_properties
        self.json_path = json_path
        self.name = name



        if self.json_path:
            if is_yaml:
                self.json_obj = yaml.safe_load(self.io_str)
            else:
                self.json_obj = json.load(self.io_str)
            for path in self.json_path:
                self.json_obj = self.json_obj[path]
        else:
            if is_yaml:
                self.json_obj = yaml.safe_load(self.io_str)
            else:
                self.json_obj = json.load(self.io_str)

        if isinstance(self.json_obj, list):
            self._len = len(self.json_obj)
            self._line_num = 0
        else:
            self.json_obj = [self.json_obj]
            self._len = 0
            self._line_num = 0

        if row_limit:
            self._line_limit = row_limit
        else:
            self._line_limit = self._len

    def __iter__(self) -> Iterator:
        return self

    def __next__(self) -> Dict[str, Any]:

        if self._line_num == self._line_limit:
            LOG.info(f"Finished processing {self.name}")
            raise StopIteration

        next_obj = self.json_obj[self._line_num]

        self._line_num += 1

        # Check that required properties exist in row
        if self.required_properties:
            properties = []
            for prop in self.required_properties:
                new_prop = check_data(next_obj, prop)
                properties.append(new_prop)

            if False in properties:
                raise ValueError(
                    f"Required properties defined for {self.name} are missing from {self.io_str.name}\n"
                    f"Missing properties: {set(self.required_properties) - set(next_obj.keys())}\n"
                    f"Row: {next_obj}"
                )

        return next_obj
