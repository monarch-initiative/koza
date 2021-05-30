import importlib
import logging
from pathlib import Path
from typing import Dict, Iterable

import yaml

from koza.io.writer.kgx_writer import KGXWriter
from koza.io.writer.writer import KozaWriter
from koza.map_loader import load_map
from koza.model.biolink import Entity
from koza.model.config.source_config import MapFileConfig, OutputFormat, PrimaryFileConfig
from koza.model.source import Source, SourceFile
from koza.validator.exceptions import MapItemException

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
        self.writer: KozaWriter = KGXWriter(self.output_dir, self.output_format, self.source.name)

        logging.getLogger(__name__)

        for src_file in source.source_files:

            with open(src_file, 'r') as source_file_fh:
                source_file_config = PrimaryFileConfig(**yaml.safe_load(source_file_fh))

            if not source_file_config.transform_code:
                # look for it alongside the source conf as a .py file
                source_file_config.transform_code = (
                    str(Path(src_file).parent / Path(src_file).stem) + '.py'
                )

            # todo: make sure the same map isn't loaded more than once?
            if source_file_config.depends_on is not None:
                for map_file in source_file_config.depends_on:
                    with open(map_file, 'r') as map_file_fh:
                        map_file_config = MapFileConfig(**yaml.safe_load(map_file_fh))

                    # todo: look for a map file py alongside the config to run instead
                    self.map_cache[map_file_config.name] = load_map(map_file_config)

            self.file_registry[source_file_config.name] = SourceFile(source_file_config)
            self.writer_registry[source_file_config.name] = KGXWriter(
                self.output_dir, self.output_format, self.source.name
            )

    def get_map(self, map_name: str):
        pass

    def process_sources(self):
        """
        :return:
        """
        import sys

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
                    except StopIteration:
                        break
            elif source_file.config.transform_mode == 'loop':
                importlib.import_module(transform_code)
            else:
                raise NotImplementedError

            # close the writer when the source is done processing
            self.writer_registry[source_file.config.name].finalize()

    def write(self, source_name, entities: Iterable[Entity]):
        self.writer_registry[source_name].write(entities)
