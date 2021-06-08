import logging
import re

from koza.manager.data_provider import inject_row, inject_translation_table, inject_map

LOG = logging.getLogger(__name__)

source_name = 'mimtitles'

row = inject_row(source_name)
translation_table = inject_translation_table(source_name)
map = inject_map(source_name)

entry = dict()

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

if row['Prefix'] == 'Asterisk':
    entry['type'] = translation_table.global_table['gene']

elif row['Prefix'] == 'NULL':
    entry['type'] = translation_table.global_table['Suspected']  # NCIT:C71458

elif row['Prefix'] == 'Number Sign':
    entry['type'] = translation_table.global_table['phenotype']

elif row['Prefix'] == 'Percent':
    entry['type'] = translation_table.global_table['heritable_phenotypic_marker']

elif row['Prefix'] == 'Plus':
    entry['type'] = translation_table.global_table['gene']

elif row['Prefix'] == 'Caret':  # moved|removed|split -> moved twice
    # populating a dict from an omim to a set of omims
    entry['type'] = translation_table.global_table['obsolete']
    entry['replaced by'] = []

    if row['Preferred Title; symbol'][:9] == 'MOVED TO ':
        token = row['Preferred Title; symbol'].split(' ')
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
            entry['replaced by'] = [title_symbol, token[4]]

        else:
            entry['replaced by'] = [title_symbol]

else:
    LOG.error(f"Unknown OMIM type line {row['omim_id']}")

map[row['MIM Number']] = entry
