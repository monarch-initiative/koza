#!/usr/bin/env python3
"""
Set of functions to manage input and output
"""
import gzip
import tempfile
from io import TextIOWrapper
from os import PathLike
from pathlib import Path
from typing import IO, Union

import requests

from koza.model.config.source_config import CompressionType


def open_resource(resource: Union[str, PathLike], compression: CompressionType = None) -> IO[str]:
    """
    A generic function for opening a local or remote file

    On remote files - files are written to a temporary file, returned as an IO[str]
    and then deleted upon closing.  Users of this lib should be encouraged to
    fetch remote files and store them locally using a more specialized tool
    wget --timestamping with gmake works great see
    https://github.com/monarch-initiative/DipperCache

    Currently no plans to support FTP, but note
    that requests does not support FTP (consider ftplib or urllib.request)

    :param resource: str or PathLike - local filepath or remote resource
    :param compression: str or PathLike - compression type
    :return: str, next line in resource

    """
    if Path(resource).exists():
        if compression is None:
            # Try gzip first
            try:
                file = gzip.open(resource, 'rt')
                file.read(1)
                file.seek(0)

            except OSError:
                file = open(resource, 'r')
        elif compression == CompressionType.gzip:
            file = gzip.open(resource, 'rt')
        else:
            file = open(resource, 'r')

        return file

    elif isinstance(resource, str) and resource.startswith('http'):
        tmp_file = tempfile.TemporaryFile('w+b')
        request = requests.get(resource)
        if request.status_code != 200:
            raise ValueError(f"Remote file returned {request.status_code}: {request.text}")
        tmp_file.write(request.content)
        request.close()  # not sure this is needed
        tmp_file.seek(0)
        if resource.endswith('gz') or compression == CompressionType.gzip:
            # This should be more robust, either check headers
            # or use https://github.com/ahupp/python-magic
            remote_file = gzip.open(tmp_file, 'rt')
            return remote_file

        else:
            return TextIOWrapper(tmp_file)

    else:
        raise ValueError(f"Cannot open local or remote file: {resource}")
