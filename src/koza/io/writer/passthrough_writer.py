from collections.abc import Iterable

from koza.io.writer.writer import KozaWriter
from koza.model.writer import WriterConfig


class PassthroughWriter(KozaWriter):
    def __init__(self, config: WriterConfig | None = None):
        self.config = config
        self.data = []

    def write(self, entities: Iterable):
        for item in entities:
            self.data.append(item)
            self.tally_entity(item)

    def write_nodes(self, nodes: Iterable):
        for node in nodes:
            self.data.append(node)
            self.node_count += 1

    def write_edges(self, edges: Iterable):
        for edge in edges:
            self.data.append(edge)
            self.edge_count += 1

    def finalize(self):
        pass

    def result(self):
        return self.data
