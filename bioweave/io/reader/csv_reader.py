from typing import Iterable, IO, Dict, Any, List

from csv import reader, DictReader

from bioweave.io.reader.reader import BioWeaveReader


class CSVReader:
    """
    A CSV reader modelled after csv.DictReader

    https://docs.python.org/3/library/csv.html#csv.DictReader

    The differences are:
      - Checking of field names agaisnt the header, returning
        a warning if extra fields exist and an ValueError
        if a field is missing

      - Support a type map dictionary, in which fieldnames
        can be mapped to types, and the CSVReader will attempt
        to coerce them from their str representation, eg int('42')

      - Potentially will add support a multivalued field DSL, eg
        List[str][';'] would convert a semicolon delimited multivalued
        field to a list of strings
    """

    #type_map: Dict[str, Any]

    def __init__(
            self,
            io_str: IO[str],
            fieldnames: List[str] = None,
            dialect="excel",
            *args,
            **kwargs
    ):
        super().__init__()
        self.fieldnames = fieldnames      # list of keys for the dict
        self.restkey = 'restkey'          # key to catch long rows
        kwargs['dialect'] = dialect
        self.reader = reader(io_str, *args, **kwargs)
        self.dialect = dialect
        self.line_num = 0

    def __next__(self) -> Dict[Any, Any]:
        if self.line_num == 0:
            if self.fieldnames is None:
                try:
                    self.fieldnames = next(self.reader)
                except StopIteration:
                    pass

        row = next(self.reader)
        self.line_num = self.reader.line_num

        # unlike the basic reader, we prefer not to return blanks,
        # because we will typically wind up with a dict full of None
        # values
        while row == []:
            row = next(self.reader)
        d = dict(zip(self.fieldnames, row))
        fields_len = len(self.fieldnames)
        row_len = len(row)
        if fields_len < row_len:
            d[self.restkey] = row[fields_len:]
        elif fields_len > row_len:
            for key in self.fieldnames[row_len:]:
                d[key] = self.restval
        return d
