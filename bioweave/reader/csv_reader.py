from bioweave.reader.reader import BioWeaveReader


class CSVReader(BioWeaveReader):

    def __init__(self):
        pass

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.reader)
