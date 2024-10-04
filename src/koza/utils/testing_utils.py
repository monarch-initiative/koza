import types
from typing import Union, List, Dict, Iterable

import pytest
from loguru import logger

from koza.app import KozaApp
from koza.cli_utils import get_koza_app, get_translation_table, _build_and_set_koza_app
from koza.model.config.source_config import PrimaryFileConfig
from koza.model.source import KozaSource


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
        transform_code_location: str,
        map_cache=None,
        filters=None,
        global_table=None,
        local_table=None,
    ):
        mock_source_file_config = PrimaryFileConfig(
            name=name,
            files=[],
            transform_code_location=transform_code_location,
        )
        mock_source_file = KozaSource(mock_source_file_config)
        mock_source_file._reader = data

        _build_and_set_koza_app(
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
        data: Union[Dict, List[Dict]],
        transform_code_location: str,
        map_cache=None,
        filters=None,
        global_table=None,
        local_table=None,
    ):
        koza_app = _make_mock_koza_app(
            name,
            iter(data) if isinstance(data, list) else iter([data]),
            transform_code_location,
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
