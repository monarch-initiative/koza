#### TSV Writer ####
# NOTE - May want to rename to KGXWriter at some point, if we develop writers for other models non biolink/kgx specific

from pathlib import Path
import typing as t

from ordered_set import OrderedSet

from koza.converter.kgx_converter import KGXConverter
from koza.io.utils import build_export_row
from koza.io.writer.writer import KozaWriter
from koza.model.config.sssom_config import SSSOMConfig


class TSVWriter(KozaWriter):
    def __init__(
        self,
        output_dir: t.Union[str, Path],
        source_name: str,
        node_properties: t.List[str] = None,
        edge_properties: t.List[str] = None,
        sssom_config: SSSOMConfig = None,
    ):
        self.basename = source_name
        self.dirname = output_dir
        self.delimiter = "\t"
        self.list_delimiter = "|"
        self.converter = KGXConverter()
        self.sssom_config = sssom_config

        Path(self.dirname).mkdir(parents=True, exist_ok=True)

        if node_properties:  # Make node file
            self.node_columns = TSVWriter._order_columns(node_properties, "node")
            self.nodes_file_name = Path(self.dirname if self.dirname else "", f"{self.basename}_nodes.tsv")
            self.nodeFH = open(self.nodes_file_name, "w")
            self.nodeFH.write(self.delimiter.join(self.node_columns) + "\n")

        if edge_properties:  # Make edge file
            if sssom_config:
                edge_properties = self.add_sssom_columns(edge_properties)
            self.edge_columns = TSVWriter._order_columns(edge_properties, "edge")
            self.edges_file_name = Path(self.dirname if self.dirname else "", f"{self.basename}_edges.tsv")
            self.edgeFH = open(self.edges_file_name, "w")
            self.edgeFH.write(self.delimiter.join(self.edge_columns) + "\n")

    def write(self, entities: t.Iterable) -> None:
        """Write an entities object to separate node and edge .tsv files"""

        nodes, edges = self.converter.convert(entities)

        if nodes:
            for node in nodes:
                self.write_row(node, record_type="node")

        if edges:
            for edge in edges:
                if self.sssom_config:
                    edge = self.sssom_config.apply_mapping(edge)
                self.write_row(edge, record_type="edge")

    def write_row(self, record: t.Dict, record_type: t.Literal["node", "edge"]) -> None:
        """Write a row to the underlying store.

        Args:
            record: Dict - A node or edge record
            record_type: Literal["node", "edge"] - The record_type of record
        """
        fh = self.nodeFH if record_type == "node" else self.edgeFH
        columns = self.node_columns if record_type == "node" else self.edge_columns
        row = build_export_row(record, list_delimiter=self.list_delimiter)
        values = []
        if record_type == "node":
            row["id"] = record["id"]
        for c in columns:
            if c in row:
                values.append(str(row[c]))
            else:
                values.append("")
        fh.write(self.delimiter.join(values) + "\n")

    def finalize(self):
        """Close file handles."""

        if hasattr(self, "nodeFH"):
            self.nodeFH.close()
        if hasattr(self, "edgeFH"):
            self.edgeFH.close()

    @staticmethod
    def _order_columns(cols: t.Set, record_type: t.Literal["node", "edge"]) -> OrderedSet:
        """Arrange node or edge columns in a defined order.

        Args:
            cols: Set - A set with elements in any order

        Returns:
            OrderedSet - A set with elements in a defined order
        """
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
