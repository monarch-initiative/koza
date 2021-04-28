import importlib
from pathlib import Path
from typing import Dict, Iterable

import yaml

from koza.io.writer.kgx_writer import KGXWriter
from koza.io.writer.writer import KozaWriter
from koza.model.biolink import Entity
from koza.model.config.source_config import OutputFormat, SourceFileConfig
from koza.model.source import Source, SourceFile


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
        self.map_cache: Dict[str, Dict] = {}
        self.writer: KozaWriter = KGXWriter(self.output_dir, self.output_format, self.source.name)

        for src_file in source.source_files:
            with open(src_file, 'r') as source_file_fh:
                source_file_config = SourceFileConfig(**yaml.safe_load(source_file_fh))

            if not source_file_config.transform_code:
                # look for it alongside the source conf as a .py file
                source_file_config.transform_code = (
                    str(Path(src_file).parent / Path(src_file).stem) + '.py'
                )

            self.file_registry[source_file_config.name] = SourceFile(source_file_config)

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
                    except StopIteration:
                        break
            elif source_file.config.transform_mode == 'loop':
                importlib.import_module(transform_code)
            else:
                raise NotImplementedError

    def write(self, entities: Iterable[Entity]):
        self.writer.write(entities)
        # for arg in args:
        #     print(json.dumps(arg, default=pydantic_encoder))
