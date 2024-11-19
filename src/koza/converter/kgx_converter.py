from dataclasses import asdict
from typing import Any, Dict, Iterable, List, Tuple, Union

from pydantic import BaseModel

from biolink_model.datamodel.pydanticmodel_v2 import Association, BiologicalEntity, ChemicalEntity

class KGXConverter:
    """
    Converts the biolink model to the KGX format, which splits
    data into nodes (Entity) and edges (Association)

    This format is designed around labelled property graphs
    that allow for scalar and lists as properties (Neo4J)

    https://github.com/biolink/kgx/blob/master/specification/kgx-format.md

    """

    def convert(self, entities: Iterable[Union[Association, BiologicalEntity, ChemicalEntity]]) \
      -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        for entity in entities:
            # edge entities are Associations
            if isinstance(entity, Association):
                edges.append(self.convert_edge(entity))

            # node entities are BiologicalEntity or ChemicalEntity
            elif isinstance(entity, (BiologicalEntity, ChemicalEntity)):
                nodes.append(self.convert_node(entity))

            # otherwise, not a valid entity
            else:
                raise ValueError(
                    f"Cannot convert {entity}: Can only convert Association, BiologicalEntity, or ChemicalEntity to KGX compatible dictionaries"
                )

        return nodes, edges

    def convert_node(self, node: Union[BiologicalEntity, ChemicalEntity]) -> Dict[str, Any]:
        node_set_fields = self.get_set_fields(node)
        node_set_fields["description"] = node.description # description field is not explicitly set?
        return node_set_fields

    def convert_edge(self, association: Association) -> Dict[str, Any]:
        edge_set_fields = self.get_set_fields(association)
        return edge_set_fields

    @staticmethod
    def get_set_fields(entity: BaseModel) -> Dict[str, Any]:
        fields_set_keys = entity.model_fields_set
        entity_set_fields = {key: getattr(entity, key) for key in fields_set_keys}
        entity_set_fields["category"] = entity.category # category field is not explicitly set?
        return entity_set_fields

