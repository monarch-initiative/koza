import logging
import re
from typing import Dict, List

# from koza.curie_util import load_curie_map

LOG = logging.getLogger(__name__)

curie_regexp = re.compile(r'^[a-zA-Z_]?[a-zA-Z_0-9-]*:[A-Za-z0-9_][A-Za-z0-9_.-]*[A-Za-z0-9_]*$')


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


def is_valid_curie(curie: str, ns_filter: List[str] = None) -> bool:

    # curie_map = load_curie_map()
    if not curie_regexp.match(curie):
        return False

    prefix = curie.split(":")[0]

    # if prefix not in curie_map.keys():
    #    return False

    if ns_filter and prefix not in ns_filter:
        return False

    return True
