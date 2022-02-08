import json
import os
from dataclasses import asdict
from typing import Iterable

from koza.io.writer.writer import KozaWriter
from koza.converter.kgx_converter import KGXConverter

class JSONLWriter(KozaWriter):
    def __init__(self, output_dir: str, source_name: str):

        self.output_dir = output_dir
        self.source_name = source_name

        self.converter = KGXConverter()

        os.makedirs(output_dir, exist_ok=True)

        self.nodes_file = open(f"{output_dir}/{source_name}_nodes.jsonl", "w")
        self.edges_file = open(f"{output_dir}/{source_name}_edges.jsonl", "w")

    def write(self, entities: Iterable):

        (nodes, edges) = self.converter.convert(entities)

        for n in nodes:
            node = json.dumps(n, ensure_ascii=False)
            self.nodes_file.write(node + '\n')

        if edges:
            for e in edges:
                edge = json.dumps(e, ensure_ascii=False)
                self.edges_file.write(edge + '\n')

    def finalize(self):
        self.nodes_file.close()
        self.edges_file.close()
