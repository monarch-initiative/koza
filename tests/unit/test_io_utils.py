"""
Stub for testing koza.io.utils

Can use the io lib to mock files, or the mock lib
https://docs.python.org/3/library/io.html
https://docs.python.org/3/library/unittest.mock.html

https://github.com/monarch-initiative/dipper/blob/6f1fe5bb/dipper/utils/TestUtils.py#L41
https://github.com/monarch-initiative/dipper/blob/682560f/tests/test_udp.py#L85
"""

import pytest

from koza.io.utils import get_resource_name, open_resource


def test_get_resource_name():
    resource = "/foo/bar.tsv"
    name = get_resource_name(resource)

    assert name == 'bar.tsv'

    resource = "https://foo.com/bar.tsv"
    name = get_resource_name(resource)

    assert name == 'bar.tsv'


def test_404():
    resource = "http://httpstat.us/404"
    with pytest.raises(ValueError):
        with open_resource(resource) as _:
            pass
