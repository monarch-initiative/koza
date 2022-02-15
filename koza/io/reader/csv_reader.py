import logging
from csv import reader
from typing import IO, Any, Dict, Iterator, List, Union

from koza.model.config.source_config import FieldType, HeaderMode

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

    TODO handle cases when delimiter is >1 character
    """

    def __init__(
        self,
        io_str: IO[str],
        field_type_map: Dict[str, FieldType] = None,
        delimiter: str = ",",
        header: Union[int, HeaderMode] = HeaderMode.infer,
        header_delimiter: str = None,
        dialect: str = "excel",
        skip_blank_lines: bool = True,
        name: str = "csv file",
        comment_char: str = "#",
        row_limit: int = None,
        *args,
        **kwargs,
    ):
        """
        :param io_str: Any IO stream that yields a string
                       See https://docs.python.org/3/library/io.html#io.IOBase
        :param field_type_map: A dictionary of field names and their type (using the FieldType enum)
        :param delimiter: Field delimiter (eg. '\t' ',' ' ')
        :param header: 0 based index of the file that contains the header,
                       or header mode 'infer'|'none' ( default='infer' )
                       if 'infer' will use the first non-empty and uncommented line
                       if 'none' will use the user supplied columns in field_type_map keys,
                           if field_type_map is None this will raise a ValueError

        :param header_delimiter: delimiter for the header row, default = self.delimiter
        :param dialect: csv dialect, default=excel
        :param skip_blank_lines: true to skip blank lines, false to insert NaN for blank lines,
        :param name: filename or alias
        :param comment_char: string representing a commented line, eg # or !!
        :param row_limit: int number of lines to process
        :param args: additional args to pass to csv.reader
        :param kwargs: additional kwargs to pass to csv.reader
        """
        self.io_str = io_str
        self.field_type_map = field_type_map
        self.dialect = dialect
        self.header = header
        self.header_delimiter = header_delimiter if header_delimiter else delimiter
        self.skip_blank_lines = skip_blank_lines
        self.name = name
        self.comment_char = comment_char
        self.row_limit = row_limit

        # used by _set_header
        self.line_num = 0

        # used for row_limit
        self.line_count = 0

        self._header = None

        if delimiter == '\\s':
            delimiter = ' '

        kwargs['dialect'] = dialect
        kwargs['delimiter'] = delimiter
        self.reader = reader(io_str, *args, **kwargs)

    def __iter__(self) -> Iterator:
        return self

    def __next__(self) -> Dict[str, Any]:

        if not self._header:
            self._set_header()
                
        try:
            if self.line_count == self.row_limit:
                raise StopIteration
            else:
                row = next(self.reader)
                self.line_count += 1
        except StopIteration:
            LOG.info(f"Finished processing {self.line_num} rows for {self.name}")
            raise StopIteration
        self.line_num = self.reader.line_num

        # skip blank lines
        if self.skip_blank_lines:
            while not row:
                row = next(self.reader)
        else:
            row = ['NaN' for _ in range(len(self._header))]

        # skip commented lines (this is for footers)
        if self.comment_char is not None:
            while row[0].startswith(self.comment_char):
                row = next(self.reader)

        # Check row length discrepancies for each row
        # TODO currently varying line lengths will raise an exception
        # and hard fail, we should probably make these warnings and report
        # out which lines vary
        # Could also create a custom exception and allow the client code
        # to determine what to do here
        fields_len = len(self._header)
        row_len = len(row)
        stripped_row = [val.strip() for val in row]

        # if we've made it here we can convert a row to a dict
        field_map = dict(zip(self._header, stripped_row))

        if fields_len > row_len:
            raise ValueError(
                f"CSV file {self.name} has {fields_len - row_len} fewer columns at {self.reader.line_num}"
            )

        elif fields_len < row_len:
            LOG.warning(
                f"CSV file {self.name} has {row_len - fields_len} extra columns at {self.reader.line_num}"
            )
            # Not sure if this would serve a purpose
            #
            # if not 'extra_cols' in self.field_type_map:
            #     # Create a type map for extra columns
            #     self.field_type_map['extra_cols'] = FieldType.str
            # field_map['extra_cols'] = row[fields_len:]

        typed_field_map = {}

        for field, field_value in field_map.items():
            # Take the value and coerce it using self.field_type_map (field: FieldType)
            # FIELD_TYPE is map of the field_type enum to the python
            # to built-in type or custom extras defined in the source config
            try:
                typed_field_map[field] = FIELDTYPE_CLASS[self.field_type_map[field]](field_value)
            except KeyError as key_error:
                LOG.warning(key_error)

        return typed_field_map

    def _set_header(self):
        if isinstance(self.header, int):
            while self.line_num < self.header:
                next(self.reader)
                self.line_num = self.reader.line_num
            self._header = self._parse_header_line()

            if self.field_type_map:
                self._compare_headers_to_supplied_columns()
            else:
                self.field_type_map = {field: FieldType.str for field in self._header}

        elif self.header == 'infer':
            self._header = self._parse_header_line(skip_blank_or_commented_lines=True)
            LOG.info(f"headers for {self.name} parsed as {self._header}")
            if self.field_type_map:
                self._compare_headers_to_supplied_columns()
            else:
                self.field_type_map = {field: FieldType.str for field in self._header}

        elif self.header == 'none':
            if self.field_type_map:
                self._header = list(self.field_type_map.keys())
            else:
                raise ValueError(
                    f"there is no header and columns have not been supplied\n"
                    f"configure the 'columns' property in the source yaml"
                )

    def _parse_header_line(self, skip_blank_or_commented_lines: bool = False) -> List[str]:
        """
        Parse the header line and return a list of headers
        """
        fieldnames = next(
            reader(self.io_str, **{'delimiter': self.header_delimiter, 'dialect': self.dialect})
        )
        if skip_blank_or_commented_lines:
            # there has to be a cleaner way to do this
            while not fieldnames or (
                self.comment_char is not None and fieldnames[0].startswith(self.comment_char)
            ):
                fieldnames = next(
                    reader(
                        self.io_str, **{'delimiter': self.header_delimiter, 'dialect': self.dialect}
                    )
                )

        fieldnames[0] = fieldnames[0].lstrip(self.comment_char)
        return [f.strip() for f in fieldnames]

    def _compare_headers_to_supplied_columns(self):
        """
        Compares headers to supplied columns
        :return:
        """
        configured_fields = list(self.field_type_map.keys())

        if set(configured_fields) > set(self._header):
            raise ValueError(
                f"Configured columns missing in source file {self.name}\n"
                f"{set(configured_fields) - set(self._header)}"
            )

        if set(self._header) > set(configured_fields):
            LOG.warning(
                f"Additional column(s) in source file {self.name}\n"
                f"{set(self._header) - set(configured_fields)}\n"
                f"Checking if new column(s) inserted at end of the row"
            )
            # add to type map
            for new_fields in set(self._header) - set(configured_fields):
                self.field_type_map[new_fields] = FieldType.str

        # Check if the additional columns are appended
        # not sure if this would useful or just noise
        if self._header[: len(configured_fields)] != configured_fields:
            LOG.warning(
                f"Additional columns located within configured fields\n"
                f"given: {configured_fields}\n"
                f"found: {self._header}"
            )
