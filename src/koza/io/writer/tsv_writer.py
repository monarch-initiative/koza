#### TSV Writer ####

from pathlib import Path
from typing import Dict, List, Literal, Optional, Set, TextIO

from ordered_set import OrderedSet

from koza.io.utils import build_export_row
from koza.io.writer.writer import KozaWriter


class TSVWriter(KozaWriter):
    delimiter: str = "\t"
    list_delimiter: str = "|"

    nodeFH: Optional[TextIO]
    edgeFH: Optional[TextIO]

    def init(self):
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        if self.node_properties:  # Make node file
            self.node_properties = TSVWriter._order_columns(set(self.node_properties), "node")
            nodes_file_name = Path(self.output_dir if self.output_dir else "", f"{self.source_name}_nodes.tsv")
            self.nodeFH = open(nodes_file_name, "w")
            self.nodeFH.write(self.delimiter.join(self.node_properties) + "\n")

        if self.edge_properties:  # Make edge file
            if self.sssom_config:
                self.edge_properties = self.add_sssom_columns(self.edge_properties)
            self.edge_properties = TSVWriter._order_columns(set(self.edge_properties), "edge")
            edges_file_name = Path(self.output_dir if self.output_dir else "", f"{self.source_name}_edges.tsv")
            self.edgeFH = open(edges_file_name, "w")
            self.edgeFH.write(self.delimiter.join(self.edge_properties) + "\n")

    def write_edge(self, edge: dict):
        """Write an edge to the underlying store.

        Args:
            edge: dict - An edge record
        """
        row = build_export_row(edge, list_delimiter=self.list_delimiter)
        values = self.get_columns(row, self.edge_properties)
        self.edgeFH.write(self.delimiter.join(values) + "\n")

    def write_node(self, node: dict):
        """Write a node to the underlying store.

        Args:
            node: dict - A node record
        """
        row = build_export_row(node, list_delimiter=self.list_delimiter)
        row["id"] = node["id"]
        values = self.get_columns(row, self.node_properties)
        self.nodeFH.write(self.delimiter.join(values) + "\n")

    @staticmethod
    def get_columns(row: Dict, columns) -> List[str]:
        values = []
        for c in columns:
            if c in row:
                values.append(str(row[c]))
            else:
                values.append("")
        return values

    def finalize(self):
        """Close file handles."""

        if hasattr(self, "nodeFH"):
            self.nodeFH.close()
        if hasattr(self, "edgeFH"):
            self.edgeFH.close()

    @staticmethod
    def _order_columns(cols: Set, record_type: Literal["node", "edge"]) -> OrderedSet:
        """Arrange node or edge columns in a defined order.

        Args:
            cols: Set - A set with elements in any order

        Returns:
            OrderedSet - A set with elements in a defined order
        """
        core_columns = set()
        if record_type == "node":
            core_columns = OrderedSet(["id", "category", "name", "description", "xref", "provided_by", "synonym"])
        elif record_type == "edge":
            core_columns = OrderedSet(["id", "subject", "predicate", "object", "category", "provided_by"])
        ordered_columns = OrderedSet()
        for c in core_columns:
            if c in cols:
                ordered_columns.add(c)
                cols.remove(c)
        internal_columns = set()
        remaining_columns = cols.copy()
        for c in cols:
            if c.startswith("_"):
                internal_columns.add(c)
                remaining_columns.remove(c)
        ordered_columns.update(sorted(remaining_columns))
        ordered_columns.update(sorted(internal_columns))
        return ordered_columns

    @staticmethod
    def add_sssom_columns(edge_properties: list):
        """Add SSSOM columns to a set of columns."""
        if "original_subject" not in edge_properties:
            edge_properties.append("original_subject")
        if "original_object" not in edge_properties:
            edge_properties.append("original_object")
        return edge_properties
