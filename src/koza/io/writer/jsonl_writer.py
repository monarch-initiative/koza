import json
import os
from typing import Iterable

from koza.converter.kgx_converter import KGXConverter
from koza.io.writer.writer import KozaWriter
from koza.model.writer import WriterConfig


class JSONLWriter(KozaWriter):
    def __init__(
        self,
        output_dir: str,
        source_name: str,
        config: WriterConfig,
    ):
        self.output_dir = output_dir
        self.source_name = source_name
        self.sssom_config = config.sssom_config

        self.converter = KGXConverter()

        os.makedirs(output_dir, exist_ok=True)
        if config.node_properties:
            self.nodeFH = open(f"{output_dir}/{source_name}_nodes.jsonl", "w")
        if config.edge_properties:
            self.edgeFH = open(f"{output_dir}/{source_name}_edges.jsonl", "w")

    def write(self, entities: Iterable):
        (nodes, edges) = self.converter.convert(entities)

        if nodes:
            for n in nodes:
                node = json.dumps(n, ensure_ascii=False)
                self.nodeFH.write(node + "\n")

        if edges:
            for e in edges:
                if self.sssom_config:
                    e = self.sssom_config.apply_mapping(e)
                edge = json.dumps(e, ensure_ascii=False)
                self.edgeFH.write(edge + "\n")

    def finalize(self):
        if hasattr(self, "nodeFH"):
            self.nodeFH.close()
        if hasattr(self, "edgeFH"):
            self.edgeFH.close()
