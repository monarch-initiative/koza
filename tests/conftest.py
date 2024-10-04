import types
from typing import Iterable

import pytest
from loguru import logger

from koza.app import KozaApp
from koza.utils.testing_utils import test_koza
from koza.model.config.source_config import PrimaryFileConfig
from koza.model.source import KozaSource


@pytest.fixture
def caplog(caplog):
    handler_id = logger.add(caplog.handler, format="{message}")
    yield caplog
    logger.remove(handler_id)


@pytest.fixture(scope="package")
def mock_koza():
    # This should be extracted out but for quick prototyping
    def _mock_write(self, *entities):
        self._entities = list(entities)

    def _make_mock_koza_app(
        name: str,
        data: Iterable,
        transform_code: str,
        map_cache=None,
        filters=None,
        translation_table=None,
    ):
        mock_source_file_config = PrimaryFileConfig(
            name=name,
            files=[],
            transform_code=transform_code,
        )
        mock_source_file = KozaSource(mock_source_file_config)
        mock_source_file._reader = data

        koza = KozaApp(mock_source_file)
        # TODO filter mocks
        koza.translation_table = translation_table
        koza._map_cache = map_cache
        koza.write = types.MethodType(_mock_write, koza)

        return koza

    def _transform(
        name: str,
        data: Iterable,
        transform_code: str,
        map_cache=None,
        filters=None,
        translation_table=None,
    ):
        koza_app = _make_mock_koza_app(
            name,
            data,
            transform_code,
            map_cache=map_cache,
            filters=filters,
            translation_table=translation_table,
        )
        test_koza(koza_app)
        koza_app.process_sources()
        return koza_app._entities

    return _transform
