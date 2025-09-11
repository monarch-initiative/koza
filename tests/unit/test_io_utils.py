"""
Stub for testing koza.io.utils

Can use the io lib to mock files, or the mock lib
https://docs.python.org/3/library/io.html
https://docs.python.org/3/library/unittest.mock.html

https://github.com/monarch-initiative/dipper/blob/6f1fe5bb/dipper/utils/TestUtils.py#L41
https://github.com/monarch-initiative/dipper/blob/682560f/tests/test_udp.py#L85
"""

from pathlib import Path
from tarfile import TarFile
from zipfile import ZipFile
from unittest.mock import patch, MagicMock

import pytest

from koza.io import utils as io_utils
from koza.io.utils import _sanitize_export_property


def test_404():
    """Test that open_resource raises ValueError for HTTP 404 responses."""
    # Mock the requests.get call to return a 404 status
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    
    with patch('koza.io.utils.requests.get', return_value=mock_response):
        with pytest.raises(ValueError, match="Remote file returned 404"):
            io_utils.open_resource("http://example.com/nonexistent")


def test_http():
    resource = "https://github.com/monarch-initiative/koza/blob/8a3bab998958ecbd406c6a150cbd5c009f3f2510/tests/resources/source-files/string.tsv?raw=true"
    resource = io_utils.open_resource(resource)
    assert not isinstance(resource, tuple)


def check_resource_completion(resource: io_utils.SizedResource):
    assert resource.reader.tell() == 0
    contents = [line for line in resource.reader]
    assert resource.tell() == resource.size
    return contents


def test_open_zipfile():
    resource = io_utils.open_resource("tests/resources/source-files/string-split.zip")
    assert isinstance(resource, tuple)
    zip_fh, resources = resource
    assert isinstance(zip_fh, ZipFile)
    assert zip_fh.filename == "tests/resources/source-files/string-split.zip"

    resource_1 = next(resources)
    assert resource_1.name == "string-a.tsv"
    contents = check_resource_completion(resource_1)
    assert len(contents) == 9

    resource_2 = next(resources)
    assert resource_2.name == "string-b.tsv"
    contents = check_resource_completion(resource_2)
    assert len(contents) == 11

    zip_fh.close()


def test_open_tarfile():
    resource = io_utils.open_resource("tests/resources/source-files/string-split.tar.gz")
    assert isinstance(resource, tuple)
    tar_fh, resources = resource
    assert isinstance(tar_fh, TarFile)
    assert tar_fh.name == str(Path("tests/resources/source-files/string-split.tar.gz").absolute())

    resource_1 = next(resources)
    assert resource_1.name == "string-a.tsv"
    contents = check_resource_completion(resource_1)
    assert len(contents) == 9

    resource_2 = next(resources)
    assert resource_2.name == "string-b.tsv"
    contents = check_resource_completion(resource_2)
    assert len(contents) == 11

    tar_fh.close()


def test_open_gzip():
    resource = io_utils.open_resource("tests/resources/source-files/ZFIN_PHENOTYPE_0.jsonl.gz")
    assert not isinstance(resource, tuple)
    contents = check_resource_completion(resource)
    assert len(contents) == 10

    resource.reader.close()


@pytest.mark.parametrize(
    "query",
    [
        (
            {
                "id": "A",
                "name": "Node A",
                "category": ["biolink:NamedThing", "biolink:Gene"],
            },
            {
                "id": "A",
                "name": "Node A",
                "category": "biolink:NamedThing|biolink:Gene",
            },
        ),
        (
            {
                "id": "A",
                "name": "Node A",
                "category": ["biolink:NamedThing", "biolink:Gene"],
                "xrefs": [None, "UniProtKB:123", None, "NCBIGene:456"],
            },
            {
                "id": "A",
                "name": "Node A",
                "category": "biolink:NamedThing|biolink:Gene",
                "xrefs": "UniProtKB:123|NCBIGene:456",
            },
        ),
    ],
)
def test_build_export_row(query):
    """
    Test build_export_row method.
    """
    d = io_utils.build_export_row(query[0], list_delimiter="|")
    for k, v in query[1].items():
        assert k in d
        assert d[k] == v


@pytest.mark.parametrize(
    "query",
    [
        (("category", "biolink:Gene"), ["biolink:Gene"]),
        (
            ("publications", ["PMID:123", "PMID:456", "PMID:789"]),
            "PMID:123|PMID:456|PMID:789",
        ),
        (("negated", "True"), True),
        (("negated", True), True),
        (("negated", True), True),
        (("xref", {"a", "b", "c"}), ["a", "b", "c"]),
        (("xref", ["a", "b", "c"]), "a|b|c"),
        (("valid", "True"), "True"),
        (("valid", True), True),
        (("alias", "xyz"), "xyz"),
        (("description", "Line 1\nLine 2\nLine 3"), "Line 1 Line 2 Line 3"),
    ],
)
def test_sanitize_export_property(query):
    """
    Test sanitize_export method.
    """
    value = _sanitize_export_property(query[0][0], query[0][1], list_delimiter="|")
    if isinstance(query[1], str):
        assert value == query[1]
    elif isinstance(query[1], list | set | tuple):
        for x in query[1]:
            assert x in value
    elif isinstance(query[1], bool):
        assert query[1] == value
    else:
        assert query[1] in value


@pytest.mark.parametrize(
    "input, expected",
    [
        ([1, None, 2, "", 3, " "], [1, 2, 3]),
        ({"a": 1, "b": None, "c": "", "d": 2, "e": " "}, {"a": 1, "d": 2}),
        ({"a": [1, None, 2], "b": {"c": None, "d": 3}}, {"a": [1, 2], "b": {"d": 3}}),
        ("test", "test"),
        ("", None),
        (None, None),
        (5, 5),
        (5.5, 5.5),
        (True, True),
        (False, False),
        (0, 0),  # Ensure zeroes are not turned into None
        ([0, None, 1], [0, 1]),  # Ensure zeroes in lists are not turned into None
        ({"a": 0, "b": None}, {"a": 0}),  # Ensure zeroes in dicts are not turned into None
    ],
)
def test_remove_null(input, expected):
    assert io_utils.remove_null(input) == expected


@pytest.mark.parametrize(
    "input, expected",
    [
        (None, True),
        ("", True),
        (" ", True),
        ("non-empty string", False),
        (0, False),
        (False, False),
        (True, False),
    ],
)
def test_is_null(input, expected):
    assert io_utils.is_null(input) == expected
