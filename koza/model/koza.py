from csv import DictWriter
from dataclasses import dataclass
from typing import Dict

from koza.curie_util import get_curie_map
from koza.dsl.row_filter import RowFilter
from koza.model.config.koza_config import KozaConfig
from koza.model.source import SourceFile


@dataclass(init=False)
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

    config: KozaConfig
    file_registry: Dict[str, SourceFile]
    map_registry: Dict[str, SourceFile] = None
    curie_map: Dict[str, str] = None
    # map_cache: Dict[str, Dict] = None

    def __init__(
        self,
        config: KozaConfig,
        file_registry: Dict[str, SourceFile],
        map_registry: Dict[str, SourceFile],
    ):

        if not KozaConfig.curie_map:
            self.curie_map = get_curie_map()

    def get_next_row(self, ingest_name: str):
        row_filter = RowFilter(self.file_registry[ingest_name].config.filters)

        row = next(self.file_registry[ingest_name].reader)
        while not row_filter.include_row(row):
            # TODO log filtered out lines
            row = next(self.file_registry[ingest_name].reader)

        return row

    def get_map(self, map_name: str):
        pass

    def process_sources(self):
        """
        something might go here
        :return:
        """

    def serialize(self, ingest_name: str, *args):

        output = self.file_registry[ingest_name].config

        # set the writer
        if self.config.serialization is None:
            writer = DictWriter(output, reader.fieldnames, delimiter='\t')
            writer.writeheader()
            writer.writerow(first_row)

        for row in reader:
            if output and row_filter.include_row(row):
                writer.writerow(row)
