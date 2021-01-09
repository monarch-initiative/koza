import re

from bioweave.facade.data_provider import inject_files, inject_translation_table, inject_map
from bioweave.facade.runner import next_row, info, warning, error

_ingest_name = 'mimtitles'

file, = inject_files(_ingest_name)
translation_table = inject_translation_table(_ingest_name)
map = inject_map(_ingest_name)

if file['Prefix'] == 'Asterisk':
    map['type'] = translation_table.global_table['gene']

elif file['Prefix'] == 'NULL':
    map['type'] = translation_table.global_table['Suspected']  # NCIT:C71458

elif file['Prefix'] == 'Number Sign':
    map['type'] = translation_table.global_table['phenotype']

elif file['Prefix'] == 'Percent':
    map['type'] = translation_table.global_table['heritable_phenotypic_marker']

elif file['Prefix'] == 'Plus':
    map['type'] = translation_table.global_table['has_affected_feature']

elif file['Prefix'] == 'Caret':  # moved|removed|split -> moved twice
    # populating a dict from an omim to a set of omims
    map['type'] = translation_table.global_table['obsolete']
    map['replaced by'] = []

    if file['Preferred Title; symbol'][:9] == 'MOVED TO ':
        token = file['Preferred Title; symbol'].split(' ')
        title_symbol = token[2]

        if not re.match(r'^[0-9]{6}$', title_symbol):
            error(f"Report malformed omim replacement {title_symbol}")
            # clean up ones I know about

            if title_symbol[0] == '{' and title_symbol[7] == '}':
                title_symbol = title_symbol[1:7]
                info(f"Repaired malformed omim replacement {title_symbol}")

            if len(title_symbol) == 7 and title_symbol[6] == ',':
                title_symbol = title_symbol[:6]
                info(f"Repaired malformed omim replacement {title_symbol}")

        if len(token) > 3:
            map['replaced by'] = [title_symbol, token[4]]

        else:
            map['replaced by'] = [title_symbol]

else:
    error(f"Unknown OMIM type line {file['omim_id']}")
