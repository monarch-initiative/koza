"""
Module for managing koza runs
"""

from typing import IO, Dict, List, Optional

from .io.utils import get_resource_name
from .model.config.koza_config import KozaConfig, SerializationEnum
from .model.config.source_config import ColumnFilter, CompressionType, FormatType, SourceFileConfig
from .model.koza import KozaApp
from .model.source import Source, SourceFile

KOZA_APP = None


def set_koza_app(
    koza_config: KozaConfig,
    sources: List[Source],
    file_registry: Dict[str, SourceFile],
    map_registry: Dict[str, SourceFile] = None,
) -> KozaApp:
    """
    Setter for singleton koza app object
    """
    global KOZA_APP

    KOZA_APP = KozaApp(koza_config, file_registry, map_registry)
    return KOZA_APP


def get_koza_app() -> Optional[KozaApp]:
    """
    Getter for singleton koza app object
    """
    return KOZA_APP


def run_single_resource(
    file: str,
    format: FormatType = FormatType.csv,
    delimiter: str = ',',
    header_delimiter: str = None,
    output: IO[str] = None,
    serialization: SerializationEnum = None,
    filters: List[ColumnFilter] = None,
    compression: CompressionType = None,
):

    # Get the resource
    resource_name = get_resource_name(file)

    # Since we're coming in from the command line, make the
    # koza config object by hand
    koza_config = KozaConfig(sources=[resource_name], serialization=serialization)

    # Source registry by hand
    source = SourceFile(
        SourceFileConfig(
            name=resource_name,
            files=[file],
            format=format,
            delimiter=delimiter,
            header_delimiter=header_delimiter,
            compression=compression,
            filters=filters,
        )
    )
    source_registry = {resource_name: source}

    set_koza_app(koza_config, source_registry)
