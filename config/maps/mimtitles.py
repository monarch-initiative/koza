import logging
import re

from koza.facade.data_provider import inject_files, inject_translation_table, inject_map
from koza.facade.helper import next_row

LOG = logging.getLogger(__name__)

_ingest_name = 'mimtitles'

file, = inject_files(_ingest_name)
translation_table = inject_translation_table(_ingest_name)
map = inject_map(_ingest_name)


###
# From OMIM
#  An asterisk (*) before an entry number indicates a gene.
#
# A number symbol (#) before an entry number indicates that it is a descriptive entry,
# usually of a phenotype, and does not represent a unique locus. The reason for the use
# of the number symbol is given in the first paragraph of he entry. Discussion of any gene(s)
# related to the phenotype resides in another entry(ies) as described in the first paragraph.
#
# A plus sign (+) before an entry number indicates that the entry contains the description of
# a gene of known sequence and a phenotype.
#
# A percent sign (%) before an entry number indicates that the entry describes a confirmed
# mendelian phenotype or phenotypic locus for which the underlying molecular basis is not known.
#
# No symbol before an entry number generally indicates a description of a phenotype for which
# the mendelian basis, although suspected, has not been clearly established or that the separateness
# of this phenotype from that in another entry is unclear.
#
# A caret (^) before an entry number means the entry no longer exists because it was removed
# from the database or moved to another entry as indicated.
###

if file['Prefix'] == 'Asterisk':
    map['type'] = translation_table.global_table['gene']

elif file['Prefix'] == 'NULL':
    map['type'] = translation_table.global_table['Suspected']  # NCIT:C71458

elif file['Prefix'] == 'Number Sign':
    map['type'] = translation_table.global_table['phenotype']

elif file['Prefix'] == 'Percent':
    map['type'] = translation_table.global_table['heritable_phenotypic_marker']

elif file['Prefix'] == 'Plus':
    map['type'] = translation_table.global_table['gene']

elif file['Prefix'] == 'Caret':  # moved|removed|split -> moved twice
    # populating a dict from an omim to a set of omims
    map['type'] = translation_table.global_table['obsolete']
    map['replaced by'] = []

    if file['Preferred Title; symbol'][:9] == 'MOVED TO ':
        token = file['Preferred Title; symbol'].split(' ')
        title_symbol = token[2]

        if not re.match(r'^[0-9]{6}$', title_symbol):
            LOG.error(f"Report malformed omim replacement {title_symbol}")
            # clean up ones I know about

            if title_symbol[0] == '{' and title_symbol[7] == '}':
                title_symbol = title_symbol[1:7]
                LOG.info(f"Repaired malformed omim replacement {title_symbol}")

            if len(title_symbol) == 7 and title_symbol[6] == ',':
                title_symbol = title_symbol[:6]
                LOG.info(f"Repaired malformed omim replacement {title_symbol}")

        if len(token) > 3:
            map['replaced by'] = [title_symbol, token[4]]

        else:
            map['replaced by'] = [title_symbol]

else:
    LOG.error(f"Unknown OMIM type line {file['omim_id']}")
