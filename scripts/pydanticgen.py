#!/usr/bin/env python3

"""
A pydantic generator based on the LinkML python generator

Some key differences:

- pydantic dataclasses instead of vanilla dataclasses,
  see https://pydantic-docs.helpmanual.io/usage/dataclasses/

- UriOrCurie is replaced with a Curie type as a goal to represent
  all identifiers as curies

- Identifier types are removed, eg Union[str, EntityId] is replaced with
  Union[str, Curie]

- Curies prefixes supplied by the biolink model are validated when initializing
  and setting attributes

- Type conversions, these classes will convert the following types:
  Expected          Allowed and coerced into expected
  Curie             str
  List[Curie]       str | List[str] | Curie
  List[str]         str

- Category attribute is inferred via class variables and the type hierarchy


What parts of the schema are left out (and expected downstream)

- Required attributes, eg id, should be checked or supplied downstream


Downstream code will also need to handle nested types to be compliant with
Neo4J's data model.  Nested types will need to be converted to some primitive type
(string, number, or lists of a primitive type)


Why pydantic over standard dataclasses?

  - Validation on both initializing and setting of variables

  - Built in type coercion (this is perhaps a con as Union types are handled in odd ways for now)
    see https://github.com/samuelcolvin/pydantic/issues/1423
    https://github.com/samuelcolvin/pydantic/pull/2092

  - Built in parsing of json or yaml into nested models (ie when attributes are reference types)

  - Supported by FastAPI

"""

from pathlib import Path
from typing import List, Optional, TextIO, Tuple, Union

import typer
from linkml.generators import PYTHON_GEN_VERSION
from linkml.generators.pythongen import PythonGenerator
from linkml.utils.formatutils import be, camelcase, split_line, wrapped_annotation
from linkml_model.meta import ClassDefinition, ClassDefinitionName, SchemaDefinition, SlotDefinition


class PydanticGen(PythonGenerator):
    """
    A pydantic dataclass generator

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
from typing import Optional, List, Union, Dict, ClassVar, Any

from pydantic.dataclasses import dataclass

from koza.validator.model_validator import convert_object_to_scalar, convert_objects_to_scalars

from koza.model.config.pydantic_config import PydanticConfig
from koza.model.curie import Curie
from koza.model.biolink.named_thing import Entity, Publication

metamodel_version = "{self.schema.metamodel_version}"

# Classes
{self.gen_classdefs()}

'''

    def gen_classdef(self, cls: ClassDefinition) -> str:
        """ Generate python definition for class cls """

        parentref = f'({self.formatted_element_name(cls.is_a, True) if cls.is_a else ""})'
        slotdefs = self.gen_class_variables(cls)

        wrapped_description = (
            f'\n\t"""\n\t{wrapped_annotation(be(cls.description))}\n\t"""'
            if be(cls.description)
            else ''
        )

        return (
            ('\n@dataclass(config=PydanticConfig)' if slotdefs else '')
            + f'\nclass {self.class_or_type_name(cls.name)}{parentref}:{wrapped_description}'
            + f'{self.gen_inherited_slots(cls)}'
            + f'{self.gen_class_meta(cls)}'
            + (f'\n\t{slotdefs}' if slotdefs else '')
        )

    def range_cardinality(
        self, slot: SlotDefinition, cls: Optional[ClassDefinition], positional_allowed: bool
    ) -> Tuple[str, Optional[str]]:
        """
        Overriding to switch empty_list() and empty_dict() to

        field(default_factory={list | dict})
        """
        positional_allowed = False  # Force everything to be tag values

        range_type, parent_type, _ = self.class_reference_type(slot, cls)
        pkey = self.class_identifier(slot.range)
        # Special case, inlined, identified range
        if pkey and slot.inlined and slot.multivalued:
            base_key = self.gen_class_reference(
                self.class_identifier_path(slot.range, False), slot.name
            )
            num_elements = len(self.schema.classes[slot.range].slots)
            dflt = None if slot.required and positional_allowed else 'field(default_factory=dict)'
            if num_elements == 1:
                if slot.required:
                    return f'Union[List[{base_key}], Dict[{base_key}, {range_type}]]', dflt
                else:
                    return (
                        f'Optional[Union[List[{base_key}], Dict[{base_key}, {range_type}]]]',
                        dflt,
                    )
            else:
                if slot.required:
                    return f'Union[Dict[{base_key}, {range_type}], List[{range_type}]]', dflt
                else:
                    return (
                        f'Optional[Union[Dict[{base_key}, {range_type}], List[{range_type}]]]',
                        dflt,
                    )

        # All other cases
        if slot.multivalued:
            if slot.required:
                return f'Union[{range_type}, List[{range_type}]]', (
                    None if positional_allowed else 'None'
                )
            else:
                return (
                    f'Optional[Union[{range_type}, List[{range_type}]]]',
                    'field(default_factory=list)',
                )
        elif slot.required:
            return range_type, (None if positional_allowed else 'None')
        else:
            return f'Optional[{range_type}]', 'None'

    def class_reference_type(
        self, slot: SlotDefinition, cls: Optional[ClassDefinition]
    ) -> Tuple[str, str, str]:
        """
        Return the type of a slot referencing a class

        :param slot: slot to be typed
        :param cls: owning class.  Used for generating key references
        :return: Python class reference type, most proximal type, most proximal type name
        """
        rangelist = (
            self.class_identifier_path(cls, False)
            if slot.key or slot.identifier
            else self.slot_range_path(slot)
        )
        prox_type = self.slot_range_path(slot)[-1].rsplit('.')[-1]
        prox_type_name = rangelist[-1]

        # Quote forward references - note that enums always gen at the end
        if slot.range in self.schema.enums or (
            cls
            and slot.inlined
            and slot.range in self.schema.classes
            and self.forward_reference(slot.range, cls.name)
        ):
            rangelist[-1] = f'"{rangelist[-1]}"'
        return str(self.gen_class_reference(rangelist, slot.name)), prox_type, prox_type_name

    @staticmethod
    def gen_class_reference(rangelist: List[str], slot_name: str = None) -> str:
        """
        Return a basic or a union type depending on the number of elements in range list

        Instead of the pythongen version which uses the base type and a special
        Id type, eg
        Entity -> str, EntityID

        We have a union of str, Curie, and the class, eg
        Entity -> str, Curie, Entity

        :param rangelist: List of types from distal to proximal
        :return:
        """
        base = rangelist[0].split('.')[-1]

        class_ref = ''

        if 'URIorCURIE' in rangelist:
            class_ref = f"Union[{base}, Curie]"
        elif 'Entity' in rangelist:
            if slot_name == 'id':
                class_ref = f"Union[{base}, Curie]"
            else:
                class_ref = f"Union[{base}, Curie, {rangelist[-1]}]" if len(rangelist) > 1 else base
        else:
            class_ref = f"Union[{base}, {rangelist[-1]}]" if len(rangelist) > 1 else base

        return class_ref

    def class_identifier_path(
        self, cls_or_clsname: Union[str, ClassDefinition], force_non_key: bool
    ) -> List[str]:
        """
        Return the path closure to a class identifier if the class has a key and force_non_key is false otherwise
        return a dictionary closure.

        :param cls_or_clsname: class definition
        :param force_non_key: True means inlined even if the class has a key
        :return: path
        """
        cls = (
            cls_or_clsname
            if isinstance(cls_or_clsname, ClassDefinition)
            else self.schema.classes[ClassDefinitionName(cls_or_clsname)]
        )

        # Determine whether the class has a key
        identifier_slot = None
        if not force_non_key:
            identifier_slot = self.class_identifier(cls)

        # No key or inlined, its closure is a dictionary
        if identifier_slot is None:
            # return ['dict', self.class_or_type_name(cls.name)]
            # Not certain why this is dict and if it's a model smell
            # We want everything to be str, Curie, or another Dataclass in the model
            return ['str', self.class_or_type_name(cls.name)]

        # We're dealing with a reference
        # pathname = camelcase(cls.name + ' ' + self.aliased_slot_name(identifier_slot))
        # Instead of EntityId, which means nothing for the pydantic gen
        # use the dataclass itself Entity
        pathname = camelcase(cls.name)
        if cls.is_a:
            parent_identifier_slot = self.class_identifier(cls.is_a)
            if parent_identifier_slot:
                return self.class_identifier_path(cls.is_a, False) + [pathname]
        return self.slot_range_path(identifier_slot) + [pathname]

    @staticmethod
    def _get_entity_post_init() -> str:
        return '''
    def __post_init__(self):
        # Initialize default categories if not set
        # by traversing the MRO chain
        if not self.category:
            self.category = [
                super_class._category
                for super_class in inspect.getmro(type(self))
                if hasattr(super_class, '_category')
            ]
        '''


def main(yamlfile: str):
    pydantic_generator = PydanticGen(yamlfile)
    print(pydantic_generator.serialize())


if __name__ == "__main__":
    typer.run(main)
