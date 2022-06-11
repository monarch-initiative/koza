from pathlib import Path
import yaml

from koza.model.config.source_config import FormatType, OutputFormat, PrimaryFileConfig
from koza.cli_runner import get_koza_app

config_file = 'custom-entrez-2-string.yaml' #Path(__file__).parent.parent / 'resources' / 'biolink-model.yaml'

with open(config_file, 'r') as file:
        source_config = yaml.load(file)
       
for ingest in source_config['needed_by']:
    print(ingest)

    koza_app = get_koza_app(ingest)

    row = koza_app.get_row(ingest)

    map = koza_app.get_map(ingest)

    entry = dict()

    entry["entrez"] = row["entrez"]

    map[row["STRING"]] = entry
