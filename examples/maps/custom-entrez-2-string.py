from koza.cli_runner import get_koza_app

source_name = 'custom-entrez-2-string'

koza_app = get_koza_app(source_name)

row = koza_app.get_row(source_name)

map = koza_app.get_map(source_name)

entry = dict()

entry["entrez"] = row["entrez"]

map[row["STRING"]] = entry
