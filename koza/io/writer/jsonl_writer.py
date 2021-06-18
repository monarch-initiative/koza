import json
import os
from dataclasses import asdict
from typing import List

from biolink_model_pydantic.model import Association, Entity, NamedThing

from koza.io.writer.writer import KozaWriter


class JSONLWriter(KozaWriter):
    def __init__(self, output_dir: str, source_name: str):
        self.output_dir = output_dir
        self.source_name = source_name

        os.makedirs(output_dir, exist_ok=True)

        self.nodes_file = open(f"{output_dir}/{source_name}_nodes.jsonl", "w")
        self.edges_file = open(f"{output_dir}/{source_name}_edges.jsonl", "w")

    def write(self, entities: List[Entity]):
        for entity in entities:
            if isinstance(entity, NamedThing):
                node = json.dumps(asdict(entity), ensure_ascii=False)
                self.nodes_file.write(node + '\n')
            elif isinstance(entity, Association):
                edge = json.dumps(asdict(entity), ensure_ascii=False)
                self.edges_file.write(edge + '\n')
            else:
                raise ValueError("Can only write NamedThing or Association entities")

    def finalize(self):
        self.nodes_file.close()
        self.edges_file.close()
