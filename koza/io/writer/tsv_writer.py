from typing import Iterable, List

from kgx.sink.tsv_sink import TsvSink

from koza.converter.kgx_converter import KGXConverter
from koza.io.writer.writer import KozaWriter


class TSVWriter(KozaWriter):
    def __init__(
        self, output_dir, source_name: str, node_properties: List[str], edge_properties: List[str]
    ):
        self.output_dir = output_dir
        self.source_name = source_name
        self.converter = KGXConverter()

        if node_properties and edge_properties:
            self.sink = TsvSink(
                f"{output_dir}/{source_name}",
                "tsv",
                node_properties=node_properties,
                edge_properties=edge_properties,
            )
        else:  # allow the TsvSink to set defaults if no properties are specified
            self.sink = TsvSink(f"{output_dir}/{source_name}", "tsv")

    def write(self, entities: Iterable):

        (nodes, edges) = self.converter.convert(entities)

        for node in nodes:
            self.sink.write_node(node)

        for edge in edges:
            self.sink.write_edge(edge)

    def finalize(self):
        self.sink.finalize()
