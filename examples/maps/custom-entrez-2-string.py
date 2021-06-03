from koza.manager.data_provider import inject_row, inject_map

source_name = "custom_entrez_2_string"

row = inject_row(source_name)

map = inject_map(source_name)

entry = dict()

entry["entrez"] = row["entrez"]

map[row["STRING"]] = entry
