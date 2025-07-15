"""
Custom PyYaml loaders to add support for
unique key checking and including/importing other yaml files via
an 'include!' tag, eg

x: !include some-other.yaml
y: 1

Unique key loader based on: https://stackoverflow.com/a/63215043
Include loader based on: https://matthewpburruss.com/post/yaml/ and
                         https://stackoverflow.com/a/9577670
"""

from pathlib import Path
from typing import TextIO

import yaml
from yaml import SafeLoader
from yaml.constructor import ConstructorError

from koza.io.utils import open_resource


class UniqueIncludeLoader(SafeLoader):
    """
    YAML Loader with additional support for
    - checking for duplicate keys
    - an '!include' tag for importing other yaml files
    """

    def __init__(self, stream: str | TextIO, base_filename: str):
        super().__init__(stream)
        self._base_path = Path(base_filename).parent

    def unique_construct_mapping(self, node: yaml.MappingNode, deep=False):
        mapping = []
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ConstructorError(f"while constructing a mapping for {value_node.value} found duplicate key {key}")
            mapping.append(key)
        return super().construct_mapping(node, deep)

    @classmethod
    def with_file_base(cls, base_filename: str):
        class LoaderWithBase(cls):
            def __init__(self, stream: str | TextIO):
                super().__init__(stream, base_filename)
        return LoaderWithBase


def include_constructor(loader: UniqueIncludeLoader, node: yaml.ScalarNode):
    """
    Opens some resource (local or remote file) that appears after an !include tag
    """
    filename = loader.construct_scalar(node)
    resolved_path = loader._base_path / filename
    resource = open_resource(resolved_path)
    if isinstance(resource, tuple):
        raise ValueError("Cannot load yaml from archive files")

    return yaml.load(resource.reader, Loader=UniqueIncludeLoader.with_file_base(str(resolved_path)))  # noqa: S506


UniqueIncludeLoader.add_constructor("!include", include_constructor)
