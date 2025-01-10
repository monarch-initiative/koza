from csv import reader
from typing import IO, Any, Callable, Dict, List

from koza.model.config.source_config import FieldType, CSVReaderConfig, HeaderMode

# from koza.utils.log_utils import get_logger
# logger = get_logger(__name__)
# import logging
# logger = logging.getLogger(__name__)
from loguru import logger

FIELDTYPE_CLASS: Dict[FieldType, Callable[[str], Any]] = {
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
        config: CSVReaderConfig,
        row_limit: int = 0,
        *args,
        **kwargs,
    ):
        """
        :param io_str: Any IO stream that yields a string
                       See https://docs.python.org/3/library/io.html#io.IOBase
        :param config: A configuration for the CSV reader. See model/config/source_config.py
        :param row_limit: int number of lines to process
        :param args: additional args to pass to csv.reader
        :param kwargs: additional kwargs to pass to csv.reader
        """
        self.io_str = io_str
        self.config = config
        self.row_limit = row_limit
        self.field_type_map = config.field_type_map

        # used by _set_header
        self.line_num = 0

        # used for row_limit
        self.line_count = 0

        self._header = None

        delimiter = config.delimiter

        if config.delimiter == '\\s':
            delimiter = ' '

        self.csv_args = args
        self.csv_kwargs = kwargs

        self.csv_kwargs['dialect'] = config.dialect
        self.csv_kwargs['delimiter'] = delimiter
        self.csv_reader = reader(io_str, *self.csv_args, **self.csv_kwargs)

    @property
    def header(self):
        if self._header is None:
            header = self._consume_header()
            self._ensure_field_type_map(header)
            self._compare_headers_to_supplied_columns(header)
            self._header = header
        return self._header

    def __iter__(self):
        header = self.header
        item_ct = 0
        comment_char = self.config.comment_char

        if self.field_type_map is None:
            raise ValueError("Field type map not set on CSV source")

        for row in self.csv_reader:
            if self.row_limit and item_ct >= self.row_limit:
                logger.debug("Row limit reached")
                return

            if not row:
                if self.config.skip_blank_lines:
                    continue
                else:
                    row = ['NaN' for _ in range(len(header))]

            elif comment_char and row[0].startswith(comment_char):
                continue

            row = [val.strip() for val in row]
            item = dict(zip(header, row))

            if len(item) > len(header):
                num_extra_fields = len(item) - len(header)
                logger.warning(
                    f"CSV file {self.io_str.name} has {num_extra_fields} extra columns at {self.csv_reader.line_num}"
                )

            if len(header) > len(item):
                num_missing_columns = len(header) - len(item)
                raise ValueError(
                    f"CSV file {self.io_str.name} is missing {num_missing_columns} "
                    f"column(s) at {self.csv_reader.line_num}"
                )

            typed_item: dict[str, Any] = {}

            for k, v in item.items():
                field_type = self.field_type_map.get(k, None)
                if field_type is None:
                    # FIXME: is this the right behavior? Or should we raise an error?
                    # raise ValueError(f"No field type found for field {k}")
                    field_type = FieldType.str

                # By default, use `str` as a converter (essentially a noop)
                converter = FIELDTYPE_CLASS.get(field_type, str)

                typed_item[k] = converter(v)

            item_ct += 1
            yield typed_item

        logger.info(f"Finished processing {item_ct} rows for from file {self.io_str.name}")

    def _consume_header(self):
        if self.csv_reader.line_num > 0:
            raise RuntimeError("Can only set header at beginning of file.")

        if self.config.header_mode == HeaderMode.none:
            if self.config.field_type_map is None:
                raise ValueError(
                    "Header mode was set to 'none', but no columns were supplied.\n"
                    "Configure the 'columns' property in the transform yaml."
                )
            return list(self.config.field_type_map.keys())

        if self.config.header_mode == HeaderMode.infer:
            # logger.debug(f"headers for {self.name} parsed as {self._header}")
            return self._parse_header_line(skip_blank_or_commented_lines=True)
        elif isinstance(self.config.header_mode, int):
            while self.csv_reader.line_num < self.config.header_mode:
                next(self.csv_reader)
            return self._parse_header_line()
        else:
            raise ValueError(f"Invalid header mode given: {self.config.header_mode}.")

    def _parse_header_line(self, skip_blank_or_commented_lines: bool = False) -> List[str]:
        """
        Parse the header line and return a list of headers
        """
        header_prefix = self.config.header_prefix
        comment_char = self.config.comment_char

        csv_reader = self.csv_reader

        # If the header delimiter is explicitly set create a new CSVReader using that one.
        if self.config.header_delimiter is not None:
            kwargs = self.csv_kwargs | { "delimiter": self.config.header_delimiter }
            csv_reader = reader(self.io_str, *self.csv_args, **kwargs)

        headers = next(csv_reader)

        # If a header_prefix was defined, remove that string from the first record in the first row.
        # For example, given the header_prefix of "#" and an initial CSV row of:
        #
        # #ID,LABEL,DESCRIPTION
        #
        # The headers would be ["ID", "LABEL", "DESCRIPTION"].
        #
        # This is run before skipping commented lines since a header prefix may be "#", which is the default comment
        # character.
        if headers and header_prefix:
            headers[0] = headers[0].lstrip(header_prefix)

        if skip_blank_or_commented_lines:
            while True:
                # Continue if the line is empty
                if not headers:
                    headers = next(csv_reader)
                    continue

                # Continue if the line starts with a comment character
                if comment_char and headers[0].startswith(comment_char):
                    headers = next(csv_reader)
                    continue

                break

        return [field.strip() for field in headers]

    def _ensure_field_type_map(self, header: list[str]):
        # The field type map is either set explicitly, or derived based on config.columns. If
        # neither of those are set, then set the field type map based on the parsed headers.
        if self.field_type_map is None:
            self.field_type_map = {
                key: FieldType.str
                for key in header
            }


    def _compare_headers_to_supplied_columns(self, header: list[str]):
        """
        Compares headers to supplied columns
        :return:
        """
        if self.field_type_map is None:
            raise ValueError("No field type map set for CSV reader")

        configured_fields = list(self.field_type_map.keys())

        if set(configured_fields) > set(header):
            raise ValueError(
                f"Configured columns missing in source file {self.io_str.name}\n"
                f"\t{set(configured_fields) - set(header)}"
            )

        if set(header) > set(configured_fields):
            logger.warning(
                f"Additional column(s) in source file {self.io_str.name}\n"
                f"\t{set(header) - set(configured_fields)}\n"
                f"\tChecking if new column(s) inserted at end of the row"
            )

        # Check if the additional columns are appended
        # not sure if this would useful or just noise
        if header[: len(configured_fields)] != configured_fields:
            logger.warning(
                f"Additional columns located within configured fields\n"
                f"\tgiven: {configured_fields}\n"
                f"\tfound: {header}\n"
                f"\tadditional columns: {set(header) - set(configured_fields)}"
            )
