#!/usr/bin/env python3
"""
Set of functions to manage input and output
"""
import gzip
import tempfile
from contextlib import contextmanager
from io import TextIOWrapper
from os import PathLike
from pathlib import Path
from typing import IO, Union

import requests

from bioweave.model.config.source_config import CompressionType


@contextmanager
def open_resource(resource: Union[str, PathLike], compression: CompressionType = None) -> IO[str]:
    """
    Iterates over lines from a resource, with basic support
    for compressed file formats
    For simplicity does not support FTP, but note
    that requests does not support FTP (use ftplib or urllib.request)

    :param resource: str or PathLike - local filepath or remote resource
    :param compression: str or PathLike - compression type
    :return: str, next line in resource

    """
    if Path(resource).exists():
        # Check if file is gzipped
        if compression is None or compression == CompressionType.gzip:
            try:
                file = gzip.open(resource, 'rt')

            except OSError:
                file = open(resource, 'r')
        else:
            file = open(resource, 'r')

        try:
            yield file
        finally:
            file.close()

    elif resource.startswith('http'):
        tmp_file = tempfile.TemporaryFile('w+b')
        request = requests.get(resource)
        tmp_file.write(request.content)
        tmp_file.seek(0)
        if resource.endswith('gz') or compression == CompressionType.gzip:
            # This should be more robust, either check headers
            # or use https://github.com/ahupp/python-magic
            remote_file = gzip.open(tmp_file, 'rt')
            try:
                yield remote_file
            finally:
                remote_file.close()
                tmp_file.close()
        else:
            try:
                yield TextIOWrapper(tmp_file)
            finally:
                tmp_file.close()

    else:
        raise ValueError(f"Cannot open resource: {resource}")
