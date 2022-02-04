#### TSV Writer ####
#
# Notes: 
# - May want to rename to KGXWriter at some point, if we develop writers for other models non biolink/kgx specific

import os

from typing import Iterable, List, Dict, Set, Optional
from ordered_set import OrderedSet

from koza.converter.kgx_converter import KGXConverter
from koza.io.utils import build_export_row
from koza.io.writer.writer import KozaWriter

#from kgx.sink.tsv_sink import TsvSink
class TSVWriter(KozaWriter): 
    def __init__(
        self, output_dir, source_name: str, node_properties: List[str], edge_properties: List[str]
    ):
        self.dirname = output_dir
        self.basename = source_name

        self.node_properties = node_properties
        self.edge_properties = edge_properties

        self.delimiter = "\t"
        self.converter = KGXConverter()
        
        self.nodes_file_basename = f"{self.basename}_nodes.tsv"
        self.edges_file_basename = f"{self.basename}_edges.tsv"
        
        if not node_properties or not edge_properties:
            raise ValueError("node_properties and edge_properties must be provided to TSVWriter class.\nMake sure you define node and edge properties in your source config yaml.")

        """
        if core_edge_properies not in edge_properties:
            you gotta set these
        """
        
        self.ordered_node_columns = TSVWriter._order_node_columns(self.node_properties)
        self.ordered_edge_columns = TSVWriter._order_edge_columns(self.edge_properties)

        self.list_delimiter = "|"

        # Create output directory
        os.makedirs(self.dirname, exist_ok=True)

        # Create and write to nodes output file
        self.nodes_file_name = os.path.join(
            self.dirname if self.dirname else "", self.nodes_file_basename
        )
        self.NFH = open(self.nodes_file_name, "w")
        self.NFH.write(self.delimiter.join(self.ordered_node_columns) + "\n")

        # Create and write to edges output file
        self.edges_file_name = os.path.join(
            self.dirname if self.dirname else "", self.edges_file_basename
        )
        self.EFH = open(self.edges_file_name, "w")
        self.EFH.write(self.delimiter.join(self.ordered_edge_columns) + "\n")
                

    def write(self, entities: Iterable):
        """
        Accepts an "entities" object and writes to separate node and edge .tsv files
        """

        (nodes, edges) = self.converter.convert(entities)

        for node in nodes:
            self.write_node(node)

        for edge in edges:
            self.write_edge(edge)

    def write_node(self, record: Dict) -> None:
        """
        Write a node record to the underlying store.
        Parameters
        ----------
        record: Dict
            A node record
        """
        row = build_export_row(record, list_delimiter=self.list_delimiter)
        row["id"] = record["id"]
        values = []
        for c in self.ordered_node_columns:
            if c in row:
                values.append(str(row[c]))
            else:
                values.append("")
        self.NFH.write(self.delimiter.join(values) + "\n")

    def write_edge(self, record: Dict) -> None:
        """
        Write an edge record to the underlying store.
        Parameters
        ----------
        record: Dict
            An edge record
        """
        row = build_export_row(record, list_delimiter=self.list_delimiter)
        values = []
        for c in self.ordered_edge_columns:
            if c in row:
                values.append(str(row[c]))
            else:
                values.append("")
        self.EFH.write(self.delimiter.join(values) + "\n")


    def finalize(self):
        """
        Close file handles and create an archive if compression mode is defined.
        """
        self.NFH.close()
        self.EFH.close()

    @staticmethod
    def _order_node_columns(cols: Set) -> OrderedSet:
        """
        Arrange node columns in a defined order.
        Parameters
        ----------
        cols: Set
            A set with elements in any order
        Returns
        -------
        OrderedSet
            A set with elements in a defined order
        """
        node_columns = cols.copy()
        core_columns = OrderedSet(
            ["id", "category", "name", "description", "xref", "provided_by", "synonym"]
        )
        ordered_columns = OrderedSet()
        for c in core_columns:
            if c in node_columns:
                ordered_columns.add(c)
                node_columns.remove(c)
        internal_columns = set()
        remaining_columns = node_columns.copy()
        for c in node_columns:
            if c.startswith("_"):
                internal_columns.add(c)
                remaining_columns.remove(c)
        ordered_columns.update(sorted(remaining_columns))
        ordered_columns.update(sorted(internal_columns))
        return ordered_columns

    @staticmethod
    def _order_edge_columns(cols: Set) -> OrderedSet:
        """
        Arrange edge columns in a defined order.
        Parameters
        ----------
        cols: Set
            A set with elements in any order
        Returns
        -------
        OrderedSet
            A set with elements in a defined order
        """
        edge_columns = cols.copy()
        core_columns = OrderedSet(
            [
                "id",
                "subject",
                "predicate",
                "object",
                "category",
                "relation",
                "provided_by",
            ]
        )
        ordered_columns = OrderedSet()
        for c in core_columns:
            if c in edge_columns:
                ordered_columns.add(c)
                edge_columns.remove(c)
        internal_columns = set()
        remaining_columns = edge_columns.copy()
        for c in edge_columns:
            if c.startswith("_"):
                internal_columns.add(c)
                remaining_columns.remove(c)
        ordered_columns.update(sorted(remaining_columns))
        ordered_columns.update(sorted(internal_columns))
        return ordered_columns