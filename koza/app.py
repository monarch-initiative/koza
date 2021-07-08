import importlib
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Iterable

import yaml
from pydantic.error_wrappers import ValidationError

from koza.exceptions import MapItemException
from koza.io.writer.jsonl_writer import JSONLWriter
from koza.io.writer.tsv_writer import TSVWriter
from koza.io.writer.writer import KozaWriter
from koza.model.config.source_config import MapFileConfig, OutputFormat
from koza.model.curie_cleaner import CurieCleaner
from koza.model.map_dict import MapDict
from koza.model.source import Source, SourceFile

LOG = logging.getLogger(__name__)


class KozaApp:
    """
    Class that holds all configuration information for Koza

    Note that this is intended to be a singleton
    that is instantiated in biolink_runner and that
    object either imported in other modules, or
    passed in via a function

    Note that this borders on some anti-patterns
    - singleton as global
    - god object

    So this particular code should be re-evaluated post prototype

    Hoping that making all attributes read-only offsets some downsides
    of this approach (multi threading would be fine)
    """

    def __init__(
        self,
        source: Source,
        output_dir: str = './output',
        output_format: OutputFormat = OutputFormat('jsonl'),
    ):
        self.source = source
        self.output_dir = output_dir
        self.output_format = output_format
        self.file_registry: Dict[str, SourceFile] = {}
        self.map_registry: Dict[str, SourceFile] = {}
        self.writer_registry: Dict[str, KozaWriter] = {}
        self.map_cache: Dict[str, Dict] = {}
        self.curie_cleaner: CurieCleaner = CurieCleaner()

        logging.getLogger(__name__)

        for source_file in source.source_files:

            if not source_file.config.transform_code:
                # look for it alongside the source conf as a .py file
                source_file.config.transform_code = (
                    str(source_file.config.path.parent / source_file.config.path.stem) + '.py'
                )

            if source_file.config.depends_on is not None:
                for map_file in source_file.config.depends_on:
                    if map_file_config.name not in self.map_cache:
                        with open(map_file, 'r') as map_file_fh:
                            map_file_config = MapFileConfig(**yaml.safe_load(map_file_fh))
                            map_file_config.transform_code = (
                                str(Path(map_file).parent / Path(map_file).stem) + '.py'
                            )
                        self.map_registry[map_file_config.name] = SourceFile(map_file_config)

            self.file_registry[source_file.config.name] = source_file

            output_name = f"{source.name}.{source_file.config.name}"
            self.writer_registry[source_file.config.name] = self.get_writer(
                output_name, source_file.config.node_properties, source_file.config.edge_properties
            )

    def get_writer(self, name, node_properties, edge_properties):
        if self.output_format == OutputFormat.tsv:
            return TSVWriter(self.output_dir, name, node_properties, edge_properties)

        elif self.output_format == OutputFormat.jsonl:
            return JSONLWriter(self.output_dir, name)

    def get_map(self, map_name: str):
        pass

    def process_sources(self):
        """
        :return:
        """
        import sys

        for map_file in self.map_registry.values():
            if map_file.config.name not in self.map_cache:
                self.load_map(map_file.config)

        for source_file in self.file_registry.values():
            parent_path = Path(source_file.config.transform_code).parent
            transform_code = Path(source_file.config.transform_code).stem
            sys.path.append(str(parent_path))
            is_first = True
            transform_module = None

            if source_file.config.transform_mode == 'flat':
                while True:
                    try:
                        if is_first:
                            transform_module = importlib.import_module(transform_code)
                            is_first = False
                        else:
                            importlib.reload(transform_module)
                    except MapItemException as mie:
                        LOG.warning(f"{str(mie)} not found in map")
                    except ValidationError as ve:
                        LOG.error(f"Validation error while processing: {source_file.last_row}")
                        raise ve
                    except StopIteration:
                        break
            elif source_file.config.transform_mode == 'loop':
                if transform_code not in sys.modules.keys():
                    importlib.import_module(transform_code)
                else:
                    importlib.reload(importlib.import_module(transform_code))
            else:
                raise NotImplementedError

            # close the writer when the source is done processing
            self.writer_registry[source_file.config.name].finalize()

            # remove directory from sys.path to prevent name clashes
            sys.path.remove(str(parent_path))

    def load_map(self, map_file_config: MapFileConfig):
        source_file = SourceFile(map_file_config)

        map = MapDict()

        self.map_cache[map_file_config.name] = map

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

    def write(self, source_name, entities: Iterable):
        self.writer_registry[source_name].write(entities)
