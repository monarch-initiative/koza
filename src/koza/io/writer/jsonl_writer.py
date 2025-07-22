import json
import os
from collections.abc import Iterable

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

    def _ensure_node_file_handle(self):
        """Create node file handle if it doesn't exist"""
        if not hasattr(self, "nodeFH"):
            self.nodeFH = open(f"{self.output_dir}/{self.source_name}_nodes.jsonl", "w")

    def _ensure_edge_file_handle(self):
        """Create edge file handle if it doesn't exist"""
        if not hasattr(self, "edgeFH"):
            self.edgeFH = open(f"{self.output_dir}/{self.source_name}_edges.jsonl", "w")

    def write(self, entities: Iterable):
        (nodes, edges) = self.converter.convert(entities)

        if nodes:
            self._ensure_node_file_handle()
            for n in nodes:
                node = json.dumps(n, ensure_ascii=False)
                self.nodeFH.write(node + "\n")

        if edges:
            self._ensure_edge_file_handle()
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
