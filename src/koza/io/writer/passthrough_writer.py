from collections.abc import Iterable

from koza.io.writer.writer import KozaWriter


class PassthroughWriter(KozaWriter):
    def __init__(self):
        self.data = []

    def write(self, entities: Iterable):
        for item in entities:
            self.data.append(item)

    def write_nodes(self, nodes: Iterable):
        for node in nodes:
            self.data.append(node)

    def write_edges(self, edges: Iterable):
        for edge in edges:
            self.data.append(edge)

    def finalize(self):
        pass

    def result(self):
        return self.data
