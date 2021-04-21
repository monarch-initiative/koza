import logging
from typing import Dict

LOG = logging.getLogger(__name__)


def is_dictionary_bimap(dictionary: Dict[str, str]) -> bool:
    """
    Test if a dictionary is a bimap
    :param dictionary:
    :return: boolean
    """
    is_bimap = True
    all_values = set()
    failed_list = []

    for val in dictionary.values():
        if val not in all_values:
            all_values.add(val)
        else:
            is_bimap = False
            failed_list.append(val)

    if not is_bimap:
        LOG.warning(f"Duplicate values in yaml: {failed_list}")

    return is_bimap
