from dataclasses import asdict
from typing import List

from biolink_model_pydantic.model import Association, Entity, NamedThing

from koza.io.writer.writer import KozaWriter


class TSVWriter(KozaWriter):
    def __init__(
        self, output_dir, source_name: str, node_properties: List[str], edge_properties: List[str]
    ):
        self.output_dir = output_dir
        self.source_name = source_name

        self.node_properties = node_properties
        self.edge_properties = edge_properties

        self.nodes_file = open(f"{output_dir}/{source_name}_nodes.tsv", "w")
        self.edges_file = open(f"{output_dir}/{source_name}_edges.tsv", "w")

    def write(self, entities: List[Entity]):

        self.nodes_file.write("\t".join(self.node_properties) + "\n")
        self.edges_file.write("\t".join(self.edge_properties) + "\n")

        for entity in entities:
            if isinstance(entity, NamedThing):
                node = self.convert_node(entity)
                self.nodes_file.write(node + '\n')
            elif isinstance(entity, Association):
                edge = self.convert_edge(entity)
                self.edges_file.write(edge + '\n')
            else:
                raise ValueError("Can only write NamedThing or Association entities")

    def finalize(self):
        self.nodes_file.close()
        self.edges_file.close()

    def convert_node(self, entity: Entity):
        return self.convert_entity(entity, self.node_properties)

    def convert_edge(self, entity: Entity):
        return self.convert_entity(entity, self.edge_properties)

    def convert_entity(self, entity, properties: List[str]):
        entity_dict = asdict(entity)

        values = []
        for prop in properties:
            value = entity_dict[prop]
            values.append(value)

        return "\t".join(values)
