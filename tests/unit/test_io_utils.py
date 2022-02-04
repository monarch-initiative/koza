"""
Stub for testing koza.io.utils

Can use the io lib to mock files, or the mock lib
https://docs.python.org/3/library/io.html
https://docs.python.org/3/library/unittest.mock.html

https://github.com/monarch-initiative/dipper/blob/6f1fe5bb/dipper/utils/TestUtils.py#L41
https://github.com/monarch-initiative/dipper/blob/682560f/tests/test_udp.py#L85
"""

import pytest

from koza.io.utils import _sanitize_export_property
from koza.io.utils import *


def test_404():
    resource = "http://httpstat.us/404"
    with pytest.raises(ValueError):
        with open_resource(resource) as _:
            pass

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
    d = build_export_row(query[0], list_delimiter="|")
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
    value = _sanitize_export_property(query[0][0], query[0][1], list_delimiter='|')
    if isinstance(query[1], str):
        assert value == query[1]
    elif isinstance(query[1], (list, set, tuple)):
        for x in query[1]:
            assert x in value
    elif isinstance(query[1], bool):
        assert query[1] == value
    else:
        assert query[1] in value