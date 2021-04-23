"""
Functions that collect biolink model objects and write them
"""
import logging

from kgx.graph.nx_graph import NxGraph
from kgx.source.graph_source import GraphSource

from ..converter.kgxconverter import KGXConverter
from ..koza_runner import get_koza_app


def collect(*args):
    koza = get_koza_app()
    converter: KGXConverter = KGXConverter()
    # converter should return nodes and edges, maybe broken down in the flattened out dictionary representation?
    # that could also be where the object -> scalar stuff happens
    #

    (nodes, edges) = converter.convert(*args)
    transformer = get_koza_app().kgx_transformer
    source: GraphSource = GraphSource()

    graph = NxGraph()

    for node in nodes:
        graph.add_node(node['id'], **node)
    for edge in edges:
        graph.add_edge(edge['subject'], edge['object'], edge['id'], **edge)

    # todo: trigger kgx validation as an option?
    kgx_validation_errors = koza.kgx_validator.validate(graph)

    if kgx_validation_errors:
        for error in kgx_validation_errors:
            logging.error(str(error))

    transformer.process(source.parse(graph), koza.sink)

    # koza.write(*args)
