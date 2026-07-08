import os
from collections.abc import Iterable
from dataclasses import asdict, is_dataclass

import orjson
from pydantic import BaseModel

from koza.converter.kgx_converter import KGXConverter
from koza.io.writer.writer import KozaWriter
from koza.model.writer import WriterConfig

_NEWLINE = b"\n"
_WRITE_BATCH = 1000


class JSONLWriter(KozaWriter):
    def __init__(
        self,
        output_dir: str,
        source_name: str,
        config: WriterConfig,
    ):
        self.output_dir = output_dir
        self.source_name = source_name
        self.config = config
        self.sssom_config = config.sssom_config

        self.converter = KGXConverter()
        self.written_node_ids = set()
        self._node_buf: list[bytes] = []
        self._edge_buf: list[bytes] = []

        os.makedirs(output_dir, exist_ok=True)

    def _ensure_node_file_handle(self):
        if not hasattr(self, "nodeFH"):
            self.nodeFH = open(f"{self.output_dir}/{self.source_name}_nodes.jsonl", "wb")

    def _ensure_edge_file_handle(self):
        if not hasattr(self, "edgeFH"):
            self.edgeFH = open(f"{self.output_dir}/{self.source_name}_edges.jsonl", "wb")

    @staticmethod
    def _serialize(entity) -> bytes:
        """Serialize an entity to a JSON line (no trailing newline).

        Uses pydantic's Rust serializer directly for BaseModel instances to skip
        the intermediate Python dict; falls back to orjson on a converter-built
        dict for dataclasses or other entity types.
        """
        if isinstance(entity, BaseModel):
            return entity.__pydantic_serializer__.to_json(entity, exclude_none=True)
        if is_dataclass(entity):
            return orjson.dumps(asdict(entity))
        return orjson.dumps(entity)

    def write(self, entities: Iterable):
        (nodes, edges) = self.converter.split_entities(entities)

        if nodes:
            self.write_nodes(nodes)

        if edges:
            self.write_edges(edges)

    def write_nodes(self, nodes: Iterable):
        if not nodes:
            return
        self._ensure_node_file_handle()
        for node in nodes:
            node_id = node.id
            if node_id in self.written_node_ids:
                continue
            self._node_buf.append(self._serialize(node))
            self._node_buf.append(_NEWLINE)
            self.written_node_ids.add(node_id)
            self.node_count += 1
            if len(self._node_buf) >= _WRITE_BATCH * 2:
                self.nodeFH.write(b"".join(self._node_buf))
                self._node_buf.clear()

    def write_edges(self, edges: Iterable, preconverted: bool = False):
        if not edges:
            return
        self._ensure_edge_file_handle()
        if self.sssom_config:
            # SSSOM mapping operates on dicts; keep the dict-based path here.
            for edge in edges:
                edge_dict = self.converter.convert_association(edge)
                edge_dict = self.sssom_config.apply_mapping(edge_dict)
                self._edge_buf.append(orjson.dumps(edge_dict))
                self._edge_buf.append(_NEWLINE)
                self.edge_count += 1
                if len(self._edge_buf) >= _WRITE_BATCH * 2:
                    self.edgeFH.write(b"".join(self._edge_buf))
                    self._edge_buf.clear()
        else:
            for edge in edges:
                self._edge_buf.append(self._serialize(edge))
                self._edge_buf.append(_NEWLINE)
                self.edge_count += 1
                if len(self._edge_buf) >= _WRITE_BATCH * 2:
                    self.edgeFH.write(b"".join(self._edge_buf))
                    self._edge_buf.clear()

    def finalize(self):
        if hasattr(self, "nodeFH"):
            if self._node_buf:
                self.nodeFH.write(b"".join(self._node_buf))
                self._node_buf.clear()
            self.nodeFH.close()
        if hasattr(self, "edgeFH"):
            if self._edge_buf:
                self.edgeFH.write(b"".join(self._edge_buf))
                self._edge_buf.clear()
            self.edgeFH.close()
