from typing import Any, Iterable, Optional

from kgx.graph.nx_graph import NxGraph
from kgx.sink import Sink
from kgx.sink.json_sink import JsonSink
from kgx.sink.jsonl_sink import JsonlSink
from kgx.sink.tsv_sink import TsvSink
from kgx.source.graph_source import GraphSource
from kgx.transformer import Transformer

from koza.converter.kgx_converter import KGXConverter
from koza.io.writer.writer import KozaWriter
from koza.model.biolink.entity import Entity
from koza.model.config.source_config import OutputFormat


class KGXWriter(KozaWriter):
    def __init__(
        self,
        output_dir: str,
        output_format: OutputFormat,
        source_name: str,
    ):
        self.output_dir = output_dir
        self.output_format = output_format
        self.source_name = source_name
        self.converter: KGXConverter = KGXConverter()
        self.transformer: Transformer = Transformer(stream=True)
        self.source: GraphSource = GraphSource()
        self.sink = self.get_sink()

    def get_sink(self) -> Sink:
        if self.output_format == 'jsonl':
            return JsonlSink(filename=f"{self.output_dir}/{self.source_name}.jsonl")
        elif self.output_format == 'json':
            return JsonSink(filename=f"{self.output_dir}/{self.source_name}.json")
        elif self.output_format == 'tsv':
            return TsvSink(filename=f"{self.output_dir}/{self.source_name}.tsv", format='tsv')

    def write(self, *entities: Iterable[Entity]):

        (nodes, edges) = self.converter.convert(*entities)

        graph = NxGraph()

        for node in nodes:
            graph.add_node(node['id'], **node)
        for edge in edges:
            graph.add_edge(edge['subject'], edge['object'], edge['id'], **edge)

        # todo: trigger kgx validation as an option? probably not here...
        # kgx_validation_errors = koza.kgx_validator.validate(graph)

        # if kgx_validation_errors:
        #    for error in kgx_validation_errors:
        #        logging.error(str(error))

        self.transformer.process(self.source.parse(graph), self.sink)
        # node and edge property lists can be passed in here, probably?
        # output_args = {}
        # self.transformer.save(output_args)
        #
        # additionally, somewhere we'll need to finalize
        # self.sink.finalize()

    def writerow(self, row: Iterable[Any]) -> Optional[int]:
        pass

    def writerows(self, rows: Iterable[Iterable[Any]]) -> Optional[int]:
        pass
