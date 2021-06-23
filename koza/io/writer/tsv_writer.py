from dataclasses import asdict
from typing import List

from biolink_model_pydantic.model import Association, Entity, NamedThing
from kgx.sink.tsv_sink import TsvSink

from koza.io.writer.writer import KozaWriter


class TSVWriter(KozaWriter):
    def __init__(
        self, output_dir, source_name: str, node_properties: List[str], edge_properties: List[str]
    ):
        self.output_dir = output_dir
        self.source_name = source_name

        if node_properties and edge_properties:
            self.sink = TsvSink(
                f"{output_dir}/{source_name}",
                "tsv",
                node_properties=node_properties,
                edge_properties=edge_properties,
            )
        else: # allow the TsvSink to set defaults if no properties are specified
            self.sink = TsvSink(
                f"{output_dir}/{source_name}",
                "tsv"
            )

    def write(self, entities: List[Entity]):

        for entity in entities:
            if isinstance(entity, NamedThing):
                self.sink.write_node(asdict(entity))
            elif isinstance(entity, Association):
                self.sink.write_edge(asdict(entity))
            else:
                raise ValueError("Can only write NamedThing or Association entities")

    def finalize(self):
        self.sink.finalize()
