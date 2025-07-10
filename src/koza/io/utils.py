"""
Set of functions to manage input and output
"""

import dataclasses
import gzip
import tarfile
import tempfile
from collections.abc import Callable, Generator
from io import TextIOWrapper
from os import PathLike
from pathlib import Path
from tarfile import TarFile, is_tarfile
from typing import Any, TextIO
from zipfile import ZipFile, is_zipfile

import requests

######################
### Reader Helpers ###
######################


@dataclasses.dataclass
class SizedResource:
    name: str
    size: int
    reader: TextIO
    tell: Callable[[], int]


def is_gzipped(filename: str):
    with gzip.open(filename, "r") as fh:
        try:
            fh.read(1)
            return True
        except gzip.BadGzipFile:
            return False
        finally:
            fh.close()


def open_resource(
    resource: str | PathLike[str],
) -> (
    SizedResource
    | tuple[ZipFile, Generator[SizedResource, None, None]]
    | tuple[TarFile, Generator[SizedResource, None, None]]
):
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
    :return: str, next line in resource

    """

    # Check if resource is a remote file
    resource_name: str | PathLike[str] | None = None

    if isinstance(resource, str) and resource.startswith("http"):
        tmp_file = tempfile.NamedTemporaryFile("w+b")
        request = requests.get(resource, timeout=10)
        if request.status_code != 200:
            raise ValueError(f"Remote file returned {request.status_code}: {request.text}")
        tmp_file.write(request.content)
        request.close()
        tmp_file.seek(0)
        resource_name = resource
        resource = tmp_file.name
    else:
        resource_name = resource

    # If resource is not remote or local, raise error
    if not Path(resource).exists():
        raise ValueError(
            f"Cannot open local or remote file: {resource}. Check the URL/path, and that the file exists, "
            "and try again."
        )

    # If resource is local, check for compression
    if is_zipfile(resource):
        zip_fh = ZipFile(resource, "r")

        def generator():
            for zip_info in zip_fh.infolist():
                extracted = zip_fh.open(zip_info, "r")
                yield SizedResource(
                    zip_info.filename,
                    zip_info.file_size,
                    TextIOWrapper(extracted),
                    extracted.tell,
                )

        return zip_fh, generator()

    elif is_tarfile(resource):
        tar_fh = tarfile.open(resource, mode="r|*")

        def generator():
            for tarinfo in tar_fh:
                extracted = tar_fh.extractfile(tarinfo)
                if extracted:
                    extracted.seekable = lambda: True
                    reader = TextIOWrapper(extracted)
                    yield SizedResource(
                        tarinfo.name,
                        tarinfo.size,
                        reader,
                        reader.tell,
                    )

        return tar_fh, generator()

    elif is_gzipped(str(resource)):
        path = Path(resource)
        fh = path.open("rb")
        gzip_fh = gzip.open(fh, "rt")
        assert isinstance(gzip_fh, TextIOWrapper)
        gzip_fh.read(1)
        gzip_fh.seek(0)
        stat = path.stat()

        return SizedResource(
            str(resource_name),
            stat.st_size,
            gzip_fh,
            lambda: fh.tell(),
        )

    # If resource is local and not compressed, open as text
    else:
        path = Path(resource)
        stat = path.stat()
        fh = path.open("r")

        return SizedResource(
            str(resource_name),
            stat.st_size,
            fh,
            fh.tell,
        )


def check_data(entry: dict[str, Any], path: str) -> bool:
    """
    Given a dot delimited JSON tag path,
    returns the value of the field in the entry.
    :param entry:
    :param path:
    :return: str value of the given path into the entry
    """
    ppart = path.split(".")
    tag = ppart.pop(0)

    while True:
        if tag in entry:
            entry = entry[tag]
            exists = True
        else:
            exists = False
        if len(ppart) == 0:
            return exists
        else:
            tag = ppart.pop(0)


######################
### Writer Helpers ###
######################

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

column_types: dict[str, type] = {
    "publications": list,
    "qualifiers": list,
    "category": list,
    "synonym": list,
    "same_as": list,
    "negated": bool,
    "xrefs": list,
}

column_types.update(provenance_slot_types)


def build_export_row(data: dict[str, Any], list_delimiter: str | None = None) -> dict[str, Any]:
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
    tidy_data: dict[str, Any] = {}
    for key, value in data.items():
        new_value = remove_null(value)
        if new_value is not None:
            tidy_data[key] = _sanitize_export_property(key, new_value, list_delimiter)
    return tidy_data


def trim(value: str) -> str:
    return value.replace("\n", " ").replace('\\"', "").replace("\t", " ")


def _sanitize_export_property(key: str, value: Any, list_delimiter: str | None = None) -> list[Any] | bool | str:
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
        if column_types[key] is list:
            if isinstance(value, list | set | tuple):
                ret: list[Any] = [
                    v.replace("\n", " ").replace('\\"', "").replace("\t", " ") if isinstance(v, str) else v
                    for v in value
                ]
                new_value = list_delimiter.join([str(x) for x in ret]) if list_delimiter else ret
            else:
                new_value = str(value).replace("\n", " ").replace('\\"', "").replace("\t", " ")
        elif column_types[key] is bool:
            try:
                new_value = bool(value)
            except Exception:
                new_value = False
        else:
            new_value = str(value).replace("\n", " ").replace('\\"', "").replace("\t", " ")
    else:
        if isinstance(value, list):
            value = [
                v.replace("\n", " ").replace('\\"', "").replace("\t", " ") if isinstance(v, str) else v for v in value
            ]
            new_value = list_delimiter.join([str(x) for x in value]) if list_delimiter else value
            column_types[key] = list
        elif isinstance(value, bool):
            try:
                new_value = bool(value)
                column_types[key] = bool  # this doesn't seem right, shouldn't column_types come from the biolink model?
            except Exception:
                new_value = False
        else:
            new_value = str(value).replace("\n", " ").replace('\\"', "").replace("\t", " ")
    return new_value


def remove_null(value: Any) -> Any:
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
    if isinstance(value, list | set | tuple):
        # value is a list, set or a tuple
        new_value = []
        for v in value:
            x = remove_null(v)
            if x is not None:
                new_value.append(x)
    elif isinstance(value, dict):
        # value is a dict
        new_value = {}
        for k, v in value.items():
            x = remove_null(v)
            if x is not None:
                new_value[k] = x
    elif isinstance(value, str):
        # value is a str
        if not is_null(value):
            new_value = value
    else:
        if not is_null(value):
            new_value = value
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
