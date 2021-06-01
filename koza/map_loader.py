import importlib
import os
import sys
from pathlib import Path

from koza.koza_runner import get_koza_app
from koza.model.config.source_config import MapFileConfig
from koza.model.map_dict import MapDict
from koza.model.source import SourceFile


def load_map(map_file_config: MapFileConfig, map_file: str = None):
    source_file = SourceFile(map_file_config)

    map = MapDict()

    koza = get_koza_app()
    koza.map_cache['map_file'] = map

    if map_file:
        map_file_config.transform_code = str(Path(map_file).parent / Path(map_file).stem) + '.py'

        if os.path.exists(map_file_config.transform_code):
            parent_path = Path(map_file_config.transform_code).parent
            transform_code = Path(map_file_config.transform_code).stem
            sys.path.append(str(parent_path))
            is_first = True
            transform_module = None

            while True:
                try:
                    if is_first:
                        transform_module = importlib.import_module(transform_code)
                        is_first = False
                    else:
                        importlib.reload(transform_module)
                except StopIteration:
                    break
    else:
        key_column = map_file_config.key
        value_columns = map_file_config.values
        for row in source_file:
            map[row[key_column]] = {
                key: value for key, value in row.items() if key in value_columns
            }
