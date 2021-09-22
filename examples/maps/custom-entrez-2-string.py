from koza.cli_runner import koza_app

source_name = "custom_entrez_2_string"

row = koza_app.get_row(source_name)

map = koza_app.get_map(source_name)

entry = dict()

entry["entrez"] = row["entrez"]

map[row["STRING"]] = entry
