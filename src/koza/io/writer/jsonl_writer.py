import json
import os
from typing import Iterable, List, Optional

from koza.converter.kgx_converter import KGXConverter
from koza.io.writer.writer import KozaWriter
from koza.model.config.sssom_config import SSSOMConfig


class JSONLWriter(KozaWriter):
    def __init__(self, output_dir: str, source_name: str, node_properties: List[str],
                 edge_properties: Optional[List[str]] = None, sssom_config: SSSOMConfig = None):
        super().__init__(output_dir, source_name, node_properties, edge_properties, sssom_config)

        os.makedirs(output_dir, exist_ok=True)
        if node_properties:
            self.nodeFH = open(f"{output_dir}/{source_name}_nodes.jsonl", "w")
        if edge_properties:
            self.edgeFH = open(f"{output_dir}/{source_name}_edges.jsonl", "w")

    def write_edge(self, edge: dict):
        edge = json.dumps(edge, ensure_ascii=False)
        self.edgeFH.write(edge + '\n')

    def write_node(self, node: dict):
        node = json.dumps(node, ensure_ascii=False)
        self.nodeFH.write(node + '\n')

    def finalize(self):
        if hasattr(self, 'nodeFH'):
            self.nodeFH.close()
        if hasattr(self, 'edgeFH'):
            self.edgeFH.close()
