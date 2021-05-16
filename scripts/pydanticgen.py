#!/usr/bin/env python3

from pathlib import Path
from typing import TextIO, Union

import typer
from linkml.generators import PYTHON_GEN_VERSION
from linkml.generators.pythongen import PythonGenerator
from linkml.utils.formatutils import be, split_line
from linkml_model.meta import SchemaDefinition


class PydanticGen(PythonGenerator):
    """
    A pydantic dataclass generator

    Why pydantic?
    - Built in parsing of nested models (ie from json or yaml) into dataclasses
    - Validation on both initializing and setting of variables
    - Supported by API
    """

    generatorname = Path(__file__).name
    generatorversion = PYTHON_GEN_VERSION

    def __init__(self, schema: Union[str, TextIO, SchemaDefinition], **kwargs):
        super().__init__(
            schema=schema,
            format='py',
            genmeta=False,
            gen_classvars=False,
            gen_slots=False,
            **kwargs,
        )

    def gen_schema(self) -> str:
        split_descripton = '\n#              '.join(
            split_line(be(self.schema.description), split_len=100)
        )
        head = (
            f'''# Auto generated from {self.schema.source_file} by {self.generatorname} version: {self.generatorversion}
# Generation date: {self.schema.generation_date}
# Schema: {self.schema.name}
#'''
            if self.schema.generation_date
            else ''
        )

        return f'''{head}
# id: {self.schema.id}
# description: {split_descripton}
# license: {be(self.schema.license)}

from dataclasses import field
from typing import ClassVar, List, Union

from pydantic.dataclasses import dataclass

from koza.validator.model_validator import convert_object_to_scalar, convert_objects_to_scalars

from koza.model.config.pydantic_config import PydanticConfig
from koza.model.curie import Curie
from koza.model.biolink.named_thing import Entity, Publication

metamodel_version = "{self.schema.metamodel_version}"

# Classes
{self.gen_classdefs()}

'''


def main(yamlfile: str):
    pydantic_generator = PydanticGen(yamlfile)
    print(pydantic_generator.serialize())


if __name__ == "__main__":
    typer.run(main)
