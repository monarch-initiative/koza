import types
from typing import Iterable

from loguru import logger
import pytest

from koza.app import KozaApp
from koza.cli_utils import get_koza_app, get_translation_table, _set_koza_app
from koza.model.config.source_config import PrimaryFileConfig
from koza.model.source import Source


def test_koza(koza: KozaApp):
    """Manually sets KozaApp for testing"""
    global koza_app
    koza_app = koza

@pytest.fixture(scope="package")
def mock_koza():
    """Mock KozaApp for testing"""

    def _mock_write(self, *entities):
        if hasattr(self, "_entities"):
            self._entities.extend(list(entities))
        else:
            self._entities = list(entities)

    def _make_mock_koza_app(
        name: str,
        data: Iterable,
        transform_code: str,
        map_cache=None,
        filters=None,
        global_table=None,
        local_table=None,
    ):
        mock_source_file_config = PrimaryFileConfig(
            name=name,
            files=[],
            transform_code=transform_code,
        )
        mock_source_file = Source(mock_source_file_config)
        mock_source_file._reader = data

        _set_koza_app(
            source=mock_source_file,
            translation_table=get_translation_table(global_table, local_table, logger),
            logger=logger,
        )
        koza = get_koza_app(name)

        # TODO filter mocks
        koza._map_cache = map_cache
        koza.write = types.MethodType(_mock_write, koza)

        return koza

    def _transform(
        name: str,
        data: Iterable,
        transform_code: str,
        map_cache=None,
        filters=None,
        global_table=None,
        local_table=None,
    ):
        koza_app = _make_mock_koza_app(
            name,
            data,
            transform_code,
            map_cache=map_cache,
            filters=filters,
            global_table=global_table,
            local_table=local_table,
        )
        test_koza(koza_app)
        koza_app.process_sources()
        if not hasattr(koza_app, "_entities"):
            koza_app._entities = []
        return koza_app._entities

    return _transform


class MockKoza:
    """Mock KozaApp for testing"""

    def __init__(
        self,
        name: str,
        data: Iterable,
        transform_code: str,
        map_cache=None,
        filters=None,
        global_table=None,
        local_table=None,
    ):
        self.name = name
        self.data = data
        self.transform_code = transform_code
        self.map_cache = map_cache
        self.filters = filters
        self.global_table = global_table
        self.local_table = local_table

        # return self.transform()

    def mock_write(self, *entities):
        if hasattr(self, "_entities"):
            self._entities.extend(list(entities))
        else:
            self._entities = list(entities)

    def make_mock_koza_app(self):
        mock_source_file_config = PrimaryFileConfig(
            name=self.name,
            files=[],
            transform_code=self.transform_code,
        )
        mock_source_file = Source(mock_source_file_config)
        mock_source_file._reader = self.data

        _set_koza_app(
            source=mock_source_file,
            translation_table=get_translation_table(self.global_table, self.local_table, logger),
            logger=logger,
        )
        koza = get_koza_app(self.name)

        # TODO filter mocks
        koza._map_cache = self.map_cache
        koza.write = types.MethodType(self.mock_write, koza)

        return koza

    def transform(self):
        koza_app = self.make_mock_koza_app()
        test_koza(koza_app)
        koza_app.process_sources()
        if not hasattr(koza_app, "_entities"):
            koza_app._entities = []
        return koza_app._entities
