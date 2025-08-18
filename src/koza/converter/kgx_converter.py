from collections.abc import Iterable
from dataclasses import asdict

from pydantic import BaseModel


class KGXConverter:
    """
    Converts the biolink model to the KGX format, which splits
    data into nodes (Entity) and edges (Association)

    This format is designed around labelled property graphs
    that allow for scalar and lists as properties (Neo4J)

    https://github.com/biolink/kgx/blob/master/specification/kgx-format.md

    """
    @staticmethod
    def split_entities(entities: Iterable) -> tuple[list, list]:
        nodes = []
        edges = []

        for entity in entities:
            # if entity has subject + object + predicate, treat as edge
            if all(hasattr(entity, attr) for attr in ["subject", "object", "predicate"]):
                edges.append(entity)

            # if entity has id and name, but not subject/object/predicate, treat as node
            elif all(hasattr(entity, attr) for attr in ["id", "name"]) and not all(
                hasattr(entity, attr) for attr in ["subject", "object", "predicate"]
            ):
                nodes.append(entity)

            # otherwise, not a valid entity
            else:
                raise ValueError(
                    f"Cannot convert {entity}: Can only convert NamedThing or Association entities to KGX "
                    "compatible dictionaries"
                )

        return nodes, edges

    @staticmethod
    def convert_node(node, exclude_none: bool = False) -> dict:
        if isinstance(node, BaseModel):
            return node.model_dump(exclude_none=exclude_none)
        return asdict(node)

    @staticmethod
    def convert_association(association, exclude_none: bool = False) -> dict:
        if isinstance(association, BaseModel):
            return association.model_dump(exclude_none=exclude_none)
        return asdict(association)
