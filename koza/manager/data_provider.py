from typing import Dict, Tuple

from ..koza_runner import get_koza_app
from ..model import TranslationTable


def inject_file(ingest_name: str) -> Dict:
    koza = get_koza_app()
    return koza.get_next_row(ingest_name)


def inject_maps(ingest_name: str) -> Tuple[Dict, ...]:
    """
    TODO
    :param ingest_name:
    :return:
    """


def inject_translation_table() -> TranslationTable:
    """"""
    koza = get_koza_app()
    return koza.source.translation_table
