import logging
from csv import reader
from typing import IO, Any, Dict, Iterator

from koza.model.config.source_config import FieldType

LOG = logging.getLogger(__name__)


FIELDTYPE_CLASS = {
    FieldType.str: str,
    FieldType.int: int,
    FieldType.float: float,
    # FieldType.Proportion: Proportion,
}


class CSVReader:
    """
    A CSV reader modelled after csv.DictReader

    https://docs.python.org/3/library/csv.html#csv.DictReader

    The differences are:
      - Checking of field names against the header, returning
        a warning if extra fields exist and an ValueError
        if a field is missing

      - Handle rows that are shorter/longer than expected
        currently handled by raising an exception

      - Support a type map dictionary, in which fieldnames
        can be mapped to types, and the CSVReader will attempt
        to coerce them from their str representation, eg int('42')

      - Potentially will add support a multivalued field DSL, eg
        List[str][';'] would convert a semicolon delimited multivalued
        field to a list of strings
    """

    def __init__(
        self,
        io_str: IO[str],
        field_type_map: Dict[str, FieldType] = None,
        delimiter: str = "\t",
        has_header: bool = True,
        header_delimiter: str = None,
        dialect: str = "excel",
        *args,
        **kwargs,
    ):
        """
        :param io_str: Any IO stream that yields a string
                       See https://docs.python.org/3/library/io.html#io.IOBase
        :param field_type_map: A dictionary of field names and their type (using the FieldType enum)
        :param delimiter: Field delimiter (eg. '\t' ',' ' ')
        :param has_header: true if the file has a header, default=True
        :param header_delimiter: delimiter for the header row, default = self.delimiter
        :param dialect: csv dialect, default=excel
        :param args: additional args to pass to csv.reader
        :param kwargs: additional kwargs to pass to csv.reader
        """
        self.io_str = io_str
        self.field_type_map = field_type_map
        self.dialect = dialect
        self.has_header = has_header
        self.header_delimiter = header_delimiter if header_delimiter else delimiter

        self.line_num = 0
        self.fieldnames = []

        kwargs['dialect'] = dialect
        kwargs['delimiter'] = delimiter
        self.reader = reader(io_str, *args, **kwargs)

    def __iter__(self) -> Iterator:
        return self

    def __next__(self) -> Dict[str, Any]:

        if self.line_num == 0:

            if not self.has_header and not self.field_type_map:
                raise ValueError(
                    f"there is no header and columns have not been supplied\n"
                    f"configure the 'columns' property in the source yaml"
                )

            fieldnames = next(
                reader(self.io_str, **{'delimiter': self.header_delimiter, 'dialect': self.dialect})
            )
            fieldnames[0].rstrip('# ').rstrip()
            self.fieldnames = fieldnames
            next(self.reader)

            if self.field_type_map:

                configured_fields = list(self.field_type_map.keys())

                if set(configured_fields) > set(fieldnames):
                    raise ValueError(
                        f"Configured columns missing in source file "
                        f"{set(configured_fields) - set(fieldnames)}"
                    )

                if set(fieldnames) > set(configured_fields):
                    LOG.warning(
                        f"Additional column(s) in source file "
                        f"{set(fieldnames) - set(configured_fields)}\n"
                        f"Checking if new column(s) inserted at end of the row"
                    )
                    # add to type map
                    for new_fields in set(fieldnames) - set(configured_fields):
                        self.field_type_map[new_fields] = FieldType.str

                # Check if the additional columns are appended
                # not sure if this would useful or just noise
                if fieldnames[: len(configured_fields)] != configured_fields:
                    LOG.warning(
                        f"Additional columns located within configured fields\n"
                        f"given: {configured_fields}\n"
                        f"found: {fieldnames}"
                    )
            else:
                self.field_type_map = {field: FieldType.str for field in fieldnames}

        else:
            self.fieldnames = self.field_type_map.keys()

        row = next(self.reader)
        self.line_num = self.reader.line_num

        # skip blank lines
        while not row:
            row = next(self.reader)

        # Check row length discrepancies for each row
        # TODO currently varying line lengths will raise an exception
        # and hard fail, we should probably make these warnings and report
        # out which lines vary
        # Could also create a custom exception and allow the client code
        # to determine what to do here
        fields_len = len(self.fieldnames)
        row_len = len(row)
        if fields_len < row_len:
            raise ValueError(f"CSV file has shorter columns at {self.reader.line_num}")
        elif fields_len > row_len:
            raise ValueError(f"CSV file has longer columns at {self.reader.line_num}")

        # if we've made it here we can convert a row to a dict
        field_map = dict(zip(self.fieldnames, row))
        typed_field_map = {}

        for field, field_value in field_map.items():
            # This is really unreadable - malkovich malkovich
            # Take the value and coerce it using self.field_type_map (field: FieldType)
            # FIELD_TYPE is map of the field_type enum to the python
            # built-in type or custom extras defined in koza
            typed_field_map[field] = FIELDTYPE_CLASS[self.field_type_map[field]](field_value)

        return typed_field_map
