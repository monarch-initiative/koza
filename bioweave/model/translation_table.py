import logging
from dataclasses import dataclass
from typing import Dict, Optional

from ..validator.map_validator import is_dictionary_bimap

LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class TranslationTable:
    """"""

    global_table: Dict[str, str]
    local_table: Dict[str, str]  # maybe bidict

    def __post_init__(self):
        if not is_dictionary_bimap(self.global_table):
            raise ValueError("Global table is not a bimap")

        if not is_dictionary_bimap(self.local_table):
            raise ValueError("Local table is not a bimap")

    def resolve_term(
        self, word: str, mandatory: Optional[bool] = True, default: Optional[str] = None
    ):
        """
        Resolve a term from a source to its preferred curie

        given a term in some source
        return global[ (local[term] | term) ] || local[term] || (term | default)

        if finding a mapping is not mandatory
        returns x | default on fall through

        This may be generalized further from any mapping
        to a global mapping only; if need be.

        :param word:  the string to find as a key in translation tables
        :param mandatory: boolean to cause failure when no key exists
        :param default: string to return if nothing is found (& not manandatory)
        :return
            value from global translation table,
            or value from local translation table,
            or the query key if finding a value is not mandatory (in this order)
        """

        if word is None:
            raise ValueError("word is required")

        # we may not agree with a remote sources use of a global term we have
        # this provides opportunity for us to override
        if word in self.local_table:
            label = self.local_table[word]
            if label in self.global_table:
                term_id = self.global_table[label]
            else:
                LOG.info("Translated to '%s' but no global term_id for: '%s'", label, word)  #
                term_id = label
        elif word in self.global_table:
            term_id = self.global_table[word]
        else:
            if mandatory:
                raise KeyError("Mapping required for: ", word)
            LOG.warning("We have no translation for: '%s'", word)

            if default is not None:
                term_id = default
            else:
                term_id = word
        return term_id
