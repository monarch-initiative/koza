"""
1...* Primary Source
1...* Serializer
1 curie Map
"""

from .model.config.source_config import FormatType, CompressionType

from .io.utils import open_resource

from .io.reader.csv_reader import CSVReader
from .io.reader.jsonl_reader import JSONLReader


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
        filter: str = None,
        compression: CompressionType = None
):
    # Get the resource
    with open_resource(file, compression) as resource_io:

        if format is FormatType.csv:
            reader = CSVReader(resource_io, delimiter=delimiter, header_delimiter=header_delimiter)
        elif format is FormatType.jsonl:
            reader = JSONLReader(resource_io)
        else:
            raise ValueError

        for _ in reader:
            pass
