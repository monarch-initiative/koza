from pathlib import Path
import importlib
import yaml

from koza.model.config.source_config import SourceFileConfig
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
    ):
        self.source = source
        self.output_dir = output_dir
        self.file_registry = {}
        self.map_registry = {}
        self.map_cache = {}

        for src_file in source.source_files:
            with open(src_file, 'r') as source_file_fh:
                source_file_config = SourceFileConfig(**yaml.safe_load(source_file_fh))

            if not source_file_config.transform_code:
                # look for it alongside the source conf as a .py file
                source_file_config.transform_code = (
                    Path(src_file).parent / Path(src_file).stem + '.py'
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
            while True:
                try:
                    importlib.import_module(transform_code)
                except StopIteration:
                    break

    def write(self, *args):
        pass
