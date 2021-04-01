"""
1...* Primary Source
1...* Serializer
1 curie Map
"""

from csv import DictWriter
from typing import IO, List

from .io.reader.csv_reader import CSVReader
from .io.reader.json_reader import JSONReader
from .io.reader.jsonl_reader import JSONLReader
from .io.utils import get_resource_name, open_resource
from .model.config.koza_config import SerializationEnum
from .model.config.source_config import CompressionType, FormatType, ColumnFilter

# def register_source(): pass

# def register_map(): pass

# def get_koza() -> Koza: pass

# def cache_maps(): pass

# def get_map_cache(): pass


def run_single_resource(
    file: str,
    format: FormatType = FormatType.csv,
    delimiter: str = ',',
    header_delimiter: str = None,
    output: IO[str] = None,
    serialization: SerializationEnum = None,
    filter_in: List[ColumnFilter] = None,
    filter_out: List[ColumnFilter] = None,
    compression: CompressionType = None,
):

    # Get the resource
    resource_name = get_resource_name(file)

    with open_resource(file, compression) as resource_io:

        if format == FormatType.csv:
            reader = CSVReader(
                resource_io,
                delimiter=delimiter,
                header_delimiter=header_delimiter,
                name=resource_name,
            )
        elif format == FormatType.jsonl:
            reader = JSONLReader(resource_io, name=resource_name)
        elif format == FormatType.json:
            reader = JSONReader(resource_io, name=resource_name)
        else:
            raise ValueError

        if format == FormatType.csv:
            # Iterate over the header(s) to get field names for writer
            first_row = next(reader)

        # set the writer
        if serialization is None:
            writer = DictWriter(output, reader.fieldnames, delimiter='\t')
            writer.writeheader()
            writer.writerow(first_row)

        for row in reader:
            if output:
                writer.writerow(row)
