from typing import Iterable
from koza.io.writer.writer import KozaWriter


class PassthroughWriter(KozaWriter):
    def __init__(self):
        self.data = []

    def write(self, entities: Iterable):
        for item in entities:
            self.data.append(item)

    def finalize(self):
        pass

    def result(self):
        return self.data
