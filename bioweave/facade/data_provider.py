from typing import Tuple, Dict

from ..model import TranslationTable


def inject_files(ingest_name: str) -> Tuple[Dict, ...]:
    pass


def inject_map(ingest_name: str) -> Dict:
    """

    TODO Should the raw map be passed as well?

    :param ingest_name:
    :return:
    """
    pass

def inject_translation_table(ingest_code: str) -> TranslationTable:
    pass