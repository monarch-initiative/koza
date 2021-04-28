from typing import List

from koza.model.biolink import Association, Entity, NamedThing


class KGXConverter:
    """
    Converts the biolink model to the KGX format, which splits
    data into nodes (Entity) and edges (Association)

    This format is designed around labelled property graphs
    that allow for scalar and lists as properties (Neo4J)

    https://github.com/biolink/kgx/blob/master/specification/kgx-format.md

    """

    def convert(self, entities: List[Entity]) -> (dict, dict):

        nodes = []
        edges = []

        for entity in entities:
            if isinstance(entity, NamedThing):
                nodes.append(self.convert_node(entity))
            elif isinstance(entity, Association):
                edges.append(self.convert_association(entity))
            else:
                raise ValueError(
                    "Can only convert NamedThing or Association entities to KGX compatible dictionaries"
                )

        return nodes, edges

    def convert_node(self, node: NamedThing) -> dict:
        return vars(node)

    def convert_association(self, association: Association) -> dict:
        return vars(association)
