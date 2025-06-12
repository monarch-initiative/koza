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

    def unique_construct_mapping(self, node: yaml.MappingNode, deep=False):
        mapping = []
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ConstructorError(f"while constructing a mapping for {value_node.value} found duplicate key {key}")
            mapping.append(key)
        return super().construct_mapping(node, deep)


def include_constructor(loader: yaml.SafeLoader, node: yaml.ScalarNode):
    """
    Opens some resource (local or remote file) that appears after an !include tag
    """
    filename = loader.construct_scalar(node)
    resource = open_resource(filename)
    if isinstance(resource, tuple):
        raise ValueError("Cannot load yaml from archive files")
    return yaml.load(resource.reader, Loader=UniqueIncludeLoader)  # noqa: S506


UniqueIncludeLoader.add_constructor("!include", include_constructor)
