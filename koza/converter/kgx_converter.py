from dataclasses import asdict
from typing import Iterable, Tuple
from pydantic import BaseModel

class KGXConverter:
    """
    Converts the biolink model to the KGX format, which splits
    data into nodes (Entity) and edges (Association)

    This format is designed around labelled property graphs
    that allow for scalar and lists as properties (Neo4J)

    https://github.com/biolink/kgx/blob/master/specification/kgx-format.md

    """

    def convert(self, entities: Iterable) -> Tuple[dict, dict]:

        nodes = []
        edges = []

        for entity in entities:

            # if entity has subject + object + predicate, treat as edge
            if all(hasattr(entity, attr) for attr in ["subject", "object", "predicate"]):
                edges.append(self.convert_association(entity))

            # if entity has id and name, but not subject/object/predicate, treat as node
            elif all(hasattr(entity, attr) for attr in ["id", "name"]) and not all(
                hasattr(entity, attr) for attr in ["subject", "object", "predicate"]
            ):
                nodes.append(self.convert_node(entity))

            # otherwise, not a
            else:
                raise ValueError(
                    f"Cannot convert {entity}: Can only convert NamedThing or Association entities to KGX compatible dictionaries"

                )

        return nodes, edges

    def convert_node(self, node) -> dict:
        if isinstance(node, BaseModel):
            return dict(node)
        return asdict(node)

    def convert_association(self, association) -> dict:
        if isinstance(association, BaseModel):
            return dict(association)
        return asdict(association)
