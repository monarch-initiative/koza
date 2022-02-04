#!/usr/bin/env python3
"""
Set of functions to manage input and output
"""
import gzip
import tempfile
from io import TextIOWrapper
from os import PathLike
from pathlib import Path
from typing import IO, Union, Any, Dict

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


##### Helper functions for Writer classes #####

# Biolink 2.0 "Knowledge Source" association slots,
# including the deprecated 'provided_by' slot
provenance_slot_types = {
    "knowledge_source": list,
    "primary_knowledge_source": str,
    "original_knowledge_source": str,
    "aggregator_knowledge_source": list,
    "supporting_data_source": list,
    "provided_by": list,
}

column_types = {
    "publications": list,
    "qualifiers": list,
    "category": list,
    "synonym": list,
    "same_as": list,
    "negated": bool,
    "xrefs": list,
}

column_types.update(provenance_slot_types)

def build_export_row(data: Dict, list_delimiter: str=None) -> Dict:
    """
    Sanitize key-value pairs in dictionary.
    This should be used to ensure proper syntax and types for node and edge data as it is exported.
    Parameters
    ----------
    data: Dict
        A dictionary containing key-value pairs
    list_delimiter: str
        Optionally provide a delimiter character or string to be used to convert lists into strings.
    Returns
    -------
    Dict
        A dictionary containing processed key-value pairs
    """
    tidy_data = {}
    for key, value in data.items():
        new_value = remove_null(value)
        if new_value:
            tidy_data[key] = _sanitize_export_property(key, new_value, list_delimiter)
    return tidy_data


def _sanitize_export_property(key: str, value: Any, list_delimiter: str=None) -> Any:
    """
    Sanitize value for a key for the purpose of export.
    Casts all values to primitive types like str or bool according to the
    specified type in ``column_types``.
    If a list_delimiter is provided lists will be converted into strings using the delimiter.
    Parameters
    ----------
    key: str
        Key corresponding to a node/edge property
    value: Any
        Value corresponding to the key
    list_delimiter: str
        Optionally provide a delimiter character or string to be used to convert lists into strings.
    Returns
    -------
    value: Any
        Sanitized value
    """
    if key in column_types:
        if column_types[key] == list:
            if isinstance(value, (list, set, tuple)):
                value = [
                    v.replace("\n", " ").replace('\\"', "").replace("\t", " ")
                    if isinstance(v, str)
                    else v
                    for v in value
                ]
                new_value = list_delimiter.join([str(x) for x in value]) if list_delimiter else value
            else:
                new_value = (
                    str(value).replace("\n", " ").replace('\\"', "").replace("\t", " ")
                )
        elif column_types[key] == bool:
            try:
                new_value = bool(value)
            except:
                new_value = False
        else:
            new_value = (
                str(value).replace("\n", " ").replace('\\"', "").replace("\t", " ")
            )
    else:
        if type(value) == list:
            value = [
                v.replace("\n", " ").replace('\\"', "").replace("\t", " ")
                if isinstance(v, str)
                else v
                for v in value
            ]
            new_value = list_delimiter.join([str(x) for x in value]) if list_delimiter else value
            column_types[key] = list
        elif type(value) == bool:
            try:
                new_value = bool(value)
                column_types[key] = bool  # this doesn't seem right, shouldn't column_types come from the biolink model?
            except:
                new_value = False
        else:
            new_value = (
                str(value).replace("\n", " ").replace('\\"', "").replace("\t", " ")
            )
    return new_value


def remove_null(input: Any) -> Any:
    """
    Remove any null values from input.
    Parameters
    ----------
    input: Any
        Can be a str, list or dict
    Returns
    -------
    Any
        The input without any null values
    """
    new_value: Any = None
    if isinstance(input, (list, set, tuple)):
        # value is a list, set or a tuple
        new_value = []
        for v in input:
            x = remove_null(v)
            if x:
                new_value.append(x)
    elif isinstance(input, dict):
        # value is a dict
        new_value = {}
        for k, v in input.items():
            x = remove_null(v)
            if x:
                new_value[k] = x
    elif isinstance(input, str):
        # value is a str
        if not is_null(input):
            new_value = input
    else:
        if not is_null(input):
            new_value = input
    return new_value


def is_null(item: Any) -> bool:
    """
    Checks if a given item is null or correspond to null.
    Parameters
    ----------
    item: Any
        The item to check
    Returns
    -------
    bool
        Whether the given item is null or not
    """
    null_values = {None, "", " "}
    return item in null_values