#!/usr/bin/env python3

import typer
from linkml.generators.pythongen import PythonGenerator


def cli(yamlfile: str):
    python_generator = PythonGenerator(yamlfile)
    predicates = []
    for slot in python_generator.schema.slots.values():
        if 'related to' in python_generator.ancestors(slot):
            predicates.append(slot.name)

    predicates = [pred.replace(' ', '_') for pred in sorted(predicates)]
    formatted_predicates = '\n'.join([f"\t'{pred}'," for pred in predicates])

    predicate_named_tuple = f'''"""
Auto generated from biolink-model.yaml by predicategen.py

A lookup named tuple for Biolink edge types (or edge labels)
Note this should be generated from the biolink yaml
"""
from collections import namedtuple

predicates = [
{formatted_predicates}
]

predicate = namedtuple('biolink_predicate', predicates)(
    *['biolink:' + predicate for predicate in predicates]
)

'''
    print(predicate_named_tuple)


if __name__ == "__main__":
    typer.run(cli)
