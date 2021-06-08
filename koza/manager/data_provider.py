from typing import Dict

from koza.koza_runner import get_koza_app
from koza.model.curie_cleaner import CurieCleaner
from koza.model.translation_table import TranslationTable


def inject_row(ingest_name: str) -> Dict:
    koza = get_koza_app()
    if ingest_name in koza.file_registry:
        return next(koza.file_registry[ingest_name])
    elif ingest_name in koza.map_registry:
        return next(koza.map_registry[ingest_name])
    else:
        raise KeyError(f"{ingest_name} not found in file or map registry")


def inject_map(map_name: str) -> Dict:
    """
    Get map associated with the specified source
    :param map_name:
    :param source_name:
    :return:
    """
    koza = get_koza_app()
    return koza.map_cache[map_name]


def inject_translation_table() -> TranslationTable:
    """"""
    koza = get_koza_app()
    return koza.source.translation_table


def inject_curie_cleaner() -> CurieCleaner:
    koza = get_koza_app()
    return koza.curie_cleaner
