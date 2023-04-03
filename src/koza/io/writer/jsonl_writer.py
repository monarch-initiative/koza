import json
import os
from typing import Iterable, List, Optional

from koza.converter.kgx_converter import KGXConverter
from koza.io.writer.writer import KozaWriter


class JSONLWriter(KozaWriter):
    def __init__(
        self,
        output_dir: str,
        source_name: str,
        node_properties: List[str],
        edge_properties: Optional[List[str]] = [],
    ):

        self.output_dir = output_dir
        self.source_name = source_name

        self.converter = KGXConverter()

        os.makedirs(output_dir, exist_ok=True)
        if node_properties:
            self.nodes_file = open(f"{output_dir}/{source_name}_nodes.jsonl", "w")
        if edge_properties:
            self.edges_file = open(f"{output_dir}/{source_name}_edges.jsonl", "w")

    def write(self, entities: Iterable):

        (nodes, edges) = self.converter.convert(entities)

        if nodes:
            for n in nodes:
                node = json.dumps(n, ensure_ascii=False)
                self.nodes_file.write(node + '\n')

        if edges:
            for e in edges:
                edge = json.dumps(e, ensure_ascii=False)
                self.edges_file.write(edge + '\n')

    def finalize(self):
        if hasattr(self, 'nodes_file'):
            self.nodes_file.close()
        if hasattr(self, 'edge_file'):
            self.edges_file.close()
