"""
Module for managing koza runs
"""

from pathlib import Path
from typing import List, Optional, Union

import yaml

from .io.utils import get_resource_name
from .model.config.source_config import (
    CompressionType,
    Filter,
    FormatType,
    OutputFormat,
    SourceFileConfig,
)
from .model.koza import KozaApp
from .model.source import Source, SourceFile

KOZA_APP = None


def set_koza_app(
    source: Source, source_files: List[SourceFile] = None, map_files: List[SourceFile] = None
) -> KozaApp:
    """
    Setter for singleton koza app object
    """
    global KOZA_APP

    KOZA_APP = KozaApp(source, source_files, map_files)
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
    output_dir: Union[str, Path] = None,
    output_format: OutputFormat = None,
    filter_file: str = None,
    compression: CompressionType = None,
):

    # Get the resource
    resource_name = get_resource_name(file)

    if not filter_file:
        with open(filter_file) as filter_fh:
            filters = Filter(**yaml.safe_load(filter_fh))

    # Mock the source
    source = Source(
        name=resource_name,
        data_dir='./data/',
        output_dir=output_dir,
        source_files=[resource_name],
        output_format=output_format,
    )

    # Source registry by hand
    source_file = SourceFile(
        SourceFileConfig(
            name=resource_name,
            files=[file],
            format=format,
            delimiter=delimiter,
            header_delimiter=header_delimiter,
            compression=compression,
            filters=filters.filter,
        )
    )

    set_koza_app(source, [source_file])
