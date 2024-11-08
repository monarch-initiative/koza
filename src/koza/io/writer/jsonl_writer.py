import json
import os
from typing import Optional, TextIO

from koza.io.writer.writer import KozaWriter


class JSONLWriter(KozaWriter):
    nodeFH: Optional[TextIO]
    edgeFH: Optional[TextIO]

    def init(self):
        os.makedirs(self.output_dir, exist_ok=True)
        if self.node_properties:
            self.nodeFH = open(f"{self.output_dir}/{self.source_name}_nodes.jsonl", "w")
        if self.edge_properties:
            self.edgeFH = open(f"{self.output_dir}/{self.source_name}_edges.jsonl", "w")

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
