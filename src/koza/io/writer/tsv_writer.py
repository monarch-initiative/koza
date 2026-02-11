#### TSV Writer ####
# NOTE - May want to rename to KGXWriter at some point, if we develop writers for other models non biolink/kgx specific

from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from ordered_set import OrderedSet

from koza.converter.kgx_converter import KGXConverter
from koza.io.utils import build_export_row
from koza.io.writer.writer import KozaWriter
from koza.model.writer import WriterConfig


class TSVWriter(KozaWriter):
    def __init__(
        self,
        output_dir: str | Path,
        source_name: str,
        config: WriterConfig,
    ):
        self.basename = source_name
        self.dirname = output_dir
        self.delimiter = "\t"
        self.list_delimiter = "|"
        self.converter = KGXConverter()
        self.sssom_config = config.sssom_config

        Path(self.dirname).mkdir(parents=True, exist_ok=True)

        node_properties = config.node_properties
        edge_properties = config.edge_properties

        if node_properties:  # Make node file
            self.node_columns = TSVWriter._order_columns(node_properties, "node")
            self.nodes_file_name = Path(self.dirname if self.dirname else "", f"{self.basename}_nodes.tsv")
            self.nodeFH = open(self.nodes_file_name, "w")
            self.nodeFH.write(self.delimiter.join(self.node_columns) + "\n")

        if edge_properties:  # Make edge file
            if config.sssom_config:
                edge_properties = self.add_sssom_columns(edge_properties, config.sssom_config)
            self.edge_columns = TSVWriter._order_columns(edge_properties, "edge")
            self.edges_file_name = Path(self.dirname if self.dirname else "", f"{self.basename}_edges.tsv")
            self.edgeFH = open(self.edges_file_name, "w")
            self.edgeFH.write(self.delimiter.join(self.edge_columns) + "\n")

    def write(self, entities: Iterable) -> None:
        """Write an entities object to separate node and edge .tsv files"""

        nodes, edges = self.converter.split_entities(entities)

        if nodes:
            self.write_nodes(nodes)

        if edges:
            self.write_edges(edges)

    def write_nodes(self, nodes: Iterable):
        for node in nodes:
            node = self.converter.convert_node(node)
            self.write_row(node, record_type="node")

    def write_edges(self, edges: Iterable):
        for edge in edges:
            edge = self.converter.convert_association(edge)
            if self.sssom_config:
                edge = self.sssom_config.apply_mapping(edge)
            self.write_row(edge, record_type="edge")

    def write_row(self, record: dict, record_type: Literal["node", "edge"]) -> None:
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
    def _order_columns(cols: list[str], record_type: Literal["node", "edge"]) -> OrderedSet[str]:
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
        ordered_columns: OrderedSet[str] = OrderedSet([])
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
    def add_sssom_columns(edge_properties: list, sssom_config):
        """Add SSSOM columns to a set of columns."""
        # Add original columns for fields that have preserve_original=True
        if hasattr(sssom_config, '_unified_field_mappings'):
            # New API structure
            for field_name, field_config in sssom_config._unified_field_mappings.items():
                if field_config['preserve_original']:
                    original_field_name = field_config['original_field_name']
                    if original_field_name not in edge_properties:
                        edge_properties.append(original_field_name)
        else:
            # Fallback for deprecated API (shouldn't happen after migration, but just in case)
            for field_name in getattr(sssom_config, 'field_target_mappings', {}):
                original_field_name = f"original_{field_name}"
                if original_field_name not in edge_properties:
                    edge_properties.append(original_field_name)
        return edge_properties
