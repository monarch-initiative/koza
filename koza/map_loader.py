from typing import Dict

from koza.model.config.source_config import MapFileConfig
from koza.model.map_dict import MapDict
from koza.model.source import SourceFile


def load_map(map_file_config: MapFileConfig) -> Dict:
    source_file = SourceFile(map_file_config)
    map = MapDict()
    key_column = map_file_config.key
    value_columns = map_file_config.values

    for row in source_file:
        map[row[key_column]] = {key: value for key, value in row.items() if key in value_columns}

    return map
