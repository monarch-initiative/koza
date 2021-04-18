from csv import DictWriter
from dataclasses import dataclass
from typing import Dict, List

from koza.curie_util import get_curie_map
from koza.model.source import Source, SourceFile


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

    source: Source
    file_registry: Dict[str, SourceFile] = None
    map_registry: Dict[str, SourceFile] = None
    curie_map: Dict[str, str] = None
    map_cache: Dict[str, Dict] = None

    def __init__(
        self,
        source: Source,
        source_files: List[SourceFile] = None,
        map_files: List[SourceFile] = None,
        curie_path: str = None,
    ):

        self.curie_map = get_curie_map(curie_path)

        # put this somewhere
        # row_filter = RowFilter(self.file_registry[ingest_name].config.filters)

        if not source_files:
            pass  # TODO try to infer

        if not map_files:
            pass  # TODO try to infer

        # TODO check that all strings match, eg
        # KozaConfig sources in source list,
        # source files, maps etc

    def get_map(self, map_name: str):
        pass

    def process_sources(self):
        """
        something might go here
        :return:
        """

    def write(self, *args):

        output = self.source.output

        # set the writer
        if self.source.output_format is None:
            writer = DictWriter(output, self.source.columns, delimiter='\t')
            writer.writeheader()
            writer.writerow(self.source)

        for row in reader:
            if output and row_filter.include_row(row):
                writer.writerow(row)
