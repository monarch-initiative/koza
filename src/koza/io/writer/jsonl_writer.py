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
        self.written_node_ids = set()

        os.makedirs(output_dir, exist_ok=True)
        self.nodeFH = open(f"{output_dir}/{source_name}_nodes.jsonl", "w")
        self.edgeFH = open(f"{output_dir}/{source_name}_edges.jsonl", "w")

    def write(self, entities: Iterable):
        (nodes, edges) = self.converter.split_entities(entities)

        if nodes:
            self.write_nodes(nodes)

        if edges:
            self.write_edges(edges)

    def write_nodes(self, nodes: Iterable):
        if nodes:
            for node in nodes:
                # if we already wrote a node with this id, skip it
                node_id = node.id
                if node_id in self.written_node_ids:
                    # TODO: track when duplicate nodes were discarded (how many? only if they have properties?)
                    continue

                node = self.converter.convert_node(node, exclude_none=True)
                node_str = json.dumps(node, ensure_ascii=False)
                self.nodeFH.write(node_str + "\n")
                self.written_node_ids.add(node_id)

    def write_edges(self, edges: Iterable, preconverted: bool = False):
        if edges:
            for edge in edges:
                edge = self.converter.convert_association(edge, exclude_none=True)
                if self.sssom_config:
                    edge = self.sssom_config.apply_mapping(edge)
                edge_str = json.dumps(edge, ensure_ascii=False)
                self.edgeFH.write(edge_str + "\n")

    def finalize(self):
        if hasattr(self, "nodeFH"):
            self.nodeFH.close()
        if hasattr(self, "edgeFH"):
            self.edgeFH.close()
