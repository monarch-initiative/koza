from koza.cli_utils import get_koza_app

source_name = 'custom-map-protein-links-detailed'
map_name = 'custom-entrez-2-string'

koza_app = get_koza_app(source_name)

row = koza_app.get_row(map_name)

map = koza_app.get_map(map_name)

entry = dict()

entry["entrez"] = row["entrez"]

map[row["STRING"]] = entry
