import importlib
import sys
from pathlib import Path
from typing import Dict, Union
import yaml

from linkml.validator import validate
from pydantic import ValidationError

from koza.converter.kgx_converter import KGXConverter
from koza.utils.exceptions import MapItemException, NextRowException
from koza.io.writer.jsonl_writer import JSONLWriter
from koza.io.writer.tsv_writer import TSVWriter
from koza.io.writer.writer import KozaWriter
from koza.io.yaml_loader import UniqueIncludeLoader
from koza.model.config.source_config import MapFileConfig, OutputFormat
from koza.model.curie_cleaner import CurieCleaner
from koza.model.map_dict import MapDict
from koza.model.source import Source
from koza.model.translation_table import TranslationTable


class KozaApp:
    """Core koza class. Stores configuration and performs transforms"""

    def __init__(
        self,
        source: Source,
        translation_table: TranslationTable = None,
        output_dir: str = './output',
        output_format: OutputFormat = OutputFormat('jsonl'),
        schema: str = None,
        node_type: str = None,
        edge_type: str = None,
        logger=None,
    ):
        self.source = source
        self.translation_table = translation_table
        self.output_dir = output_dir
        self.output_format = output_format
        self._map_registry: Dict[str, Source] = {}
        self._map_cache: Dict[str, Dict] = {}
        self.curie_cleaner: CurieCleaner = CurieCleaner()
        self.writer: KozaWriter = self._get_writer()
        self.logger = logger

        if schema:
            # self.validate = True
            # self.schema = schema
            # self.node_type = node_type
            # self.edge_type = edge_type
            self.converter = KGXConverter()
        else:
            self.validate = False

        if source.config.depends_on is not None:
            for map_file in source.config.depends_on:
                with open(map_file, 'r') as map_file_fh:
                    map_file_config = MapFileConfig(**yaml.load(map_file_fh, Loader=UniqueIncludeLoader))
                    map_file_config.transform_code = str(Path(map_file).parent / Path(map_file).stem) + '.py'
                self._map_registry[map_file_config.name] = Source(map_file_config)

    def get_map(self, map_name: str):
        map = self._map_cache[map_name]
        return map

    def get_row(self, ingest_name: str = None) -> Dict:
        if ingest_name and ingest_name == self.source.config.name:
            return next(self.source)
        elif ingest_name in self._map_registry:
            return next(self._map_registry[ingest_name])
        elif ingest_name:
            raise KeyError(f"{ingest_name} is not the name of the source file or a mapping file")
        else:
            return next(self.source)

    def process_sources(self):
        """
        Transform an entire file using ingest logic in a functionless python file
        where the path to this file is stored in source.transform_code
        or inferred by taking the name and path of the config file and looking for
        a .py file along side it (see constructor)

        Intended for decoupling ingest logic into a configuration like file
        """
        import sys

        parent_path = Path(self.source.config.transform_code).parent
        transform_code = Path(self.source.config.transform_code).stem
        sys.path.append(str(parent_path))
        is_first = True
        transform_module = None

        if self.logger:
            self.logger.info(f"Transforming source: {self.source.config.name}")
        if self.source.config.transform_mode == 'flat':
            while True:
                try:
                    if is_first:
                        transform_module = importlib.import_module(transform_code)
                        is_first = False
                    else:
                        importlib.reload(transform_module)
                except MapItemException as mie:
                    if self.logger:
                        self.logger.debug(f"{str(mie)} not found in map")
                except NextRowException:
                    continue
                except ValidationError as ve:
                    if self.logger:
                        self.logger.error(f"Validation error while processing: {self.source.last_row}")
                    raise ve
                except StopIteration:
                    break
        elif self.source.config.transform_mode == 'loop':
            if transform_code not in sys.modules.keys():
                importlib.import_module(transform_code)
            else:
                importlib.reload(importlib.import_module(transform_code))
        else:
            raise NotImplementedError

        # close the writer when the source is done processing
        self.writer.finalize()

        # remove directory from sys.path to prevent name clashes
        sys.path.remove(str(parent_path))

    def process_maps(self):
        """Initializes self._map_cache"""

        for map_file in self._map_registry.values():
            if map_file.config.name not in self._map_cache:
                self._load_map(map_file)

    @staticmethod
    def next_row():
        """
        Breaks out of the facade file and iterates to the next row in the file

        Effectively a continue statement
        See: https://docs.python.org/3/reference/simple_stmts.html#continue
        """
        raise NextRowException

    def write(self, *entities):
        # If a schema/validator is defined, validate before writing
        # if self.validate:
        if hasattr(self, 'schema'):
            (nodes, edges) = self.converter.convert(entities)
            if self.output_format == OutputFormat.tsv:
                if nodes:
                    for node in nodes:
                        validate(instance=node, target_class=self.node_type, schema=self.schema, strict=True)
                if edges:
                    for edge in edges:
                        validate(instance=edge, target_class=self.edge_type, schema=self.schema, strict=True)
            elif self.output_format == OutputFormat.jsonl:
                if nodes:
                    for node in nodes:
                        validate(instance=node, target_class=self.node_type, schema=self.schema, strict=True)
                if edges:
                    for edge in edges:
                        validate(instance=edge, target_class=self.edge_type, schema=self.schema, strict=True)

        self.writer.write(entities)

    def _get_writer(self) -> Union[TSVWriter, JSONLWriter]:
        writer_params = [
            self.output_dir,
            self.source.config.name,
            self.source.config.node_properties,
            self.source.config.edge_properties,
            self.source.config.sssom_config,
        ]
        if self.output_format == OutputFormat.tsv:
            return TSVWriter(*writer_params)

        elif self.output_format == OutputFormat.jsonl:
            return JSONLWriter(*writer_params)

    def _load_map(self, map_file: Source):
        if not isinstance(map_file.config, MapFileConfig):
            raise ValueError(f"Error loading map: {map_file.config.name} is not a MapFileConfig")

        map = MapDict()

        self._map_cache[map_file.config.name] = map

        transform_code_pth = Path(map_file.config.transform_code)

        if transform_code_pth.exists():
            parent_path = transform_code_pth.parent
            transform_code = transform_code_pth.stem
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
            key_column = map_file.config.key
            value_columns = map_file.config.values
            for row in map_file:
                map[row[key_column]] = {key: value for key, value in row.items() if key in value_columns}

    @staticmethod
    def _map_sniffer(depends_on: str):
        """
        TODO a utility function to determine if a depends_on string
        is a path to a map config file, a yaml file that should be
        interpreted as a dictionary, or a json file that should be
        interpreted as a dictionary

        See https://github.com/monarch-initiative/koza/issues/39

        :param depends_on:
        """
        pass
