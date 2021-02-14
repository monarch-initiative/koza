#!/usr/bin/env python3
"""
Set of functions to manage input and output
"""
import gzip
import tempfile
from pathlib import Path
from typing import Iterator
import requests


def get_remote_source(source: str) -> Iterator[str]:
    """
    Iterates over lines from a resource, with basic support
    for compressed file formats
    For simplicity does not support FTP, but note
    that requests does not support FTP (use ftplib or urllib.request)
    :param source: str, local filepath or remote resource
    :return: str, next line in resource
    """
    path = Path(source)
    if path.exists():
        # Check if file is gzipped
        try:
            with gzip.open(path, 'rb') as file:
                for line in file:
                    yield line.decode()
        except OSError:
            with open(path, 'r') as file:
                for line in file:
                    yield line
    elif source.startswith('http'):
        if source.endswith('gz'):
            # This should be more robust, either check headers
            # or use https://github.com/ahupp/python-magic
            tmp_f = tempfile.TemporaryFile()
            request = requests.get(source)
            tmp_f.write(request.content)
            tmp_f.seek(0)
            remote_file = gzip.GzipFile(mode='rb', fileobj=tmp_f)
            for line in remote_file:
                yield line.decode()
            tmp_f.close()
        else:
            with requests.Session() as session:
                request = session.get(source, stream=True)
                for line in request.iter_lines():
                    yield line
    else:
        raise ValueError("Cannot open resource: {}".format(source))
