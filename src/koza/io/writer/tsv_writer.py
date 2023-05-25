#### TSV Writer ####
# NOTE - May want to rename to KGXWriter at some point, if we develop writers for other models non biolink/kgx specific

from pathlib import Path
from typing import Dict, Iterable, List, Literal, Set

import numpy as np
from ordered_set import OrderedSet
from sssom.parsers import parse_sssom_table
from sssom.util import filter_prefixes, merge_msdf

from koza.converter.kgx_converter import KGXConverter
from koza.io.utils import build_export_row
from koza.io.writer.writer import KozaWriter


class TSVWriter(KozaWriter):
    def __init__(
        self, 
        output_dir, 
        source_name: str,
        node_properties: List[str] = None,
        edge_properties: List[str] = None,
        sssom_config = None,
    ):
        self.basename = source_name
        self.dirname = output_dir
        self.delimiter = "\t"
        self.list_delimiter = "|"
        self.converter = KGXConverter()

        if sssom_config:
            self.sssom_prefixes = sssom_config.prefixes
            mapping_sets = []
            for file in sssom_config.files:
                msdf = parse_sssom_table(file)
                mapping_sets.append(msdf)
            merged = merge_msdf(*mapping_sets)
            filtered_df = filter_prefixes(
                df=merged.df,
                filter_prefixes=self.sssom_prefixes,
                require_all_prefixes=False
            )
            self.sssom_df = filtered_df

        Path(self.dirname).mkdir(parents=True, exist_ok=True)

        if node_properties: # Make node file
            self.node_columns = TSVWriter._order_columns(node_properties, "node")
            self.nodes_file_name = Path(self.dirname if self.dirname else "", f"{self.basename}_nodes.tsv")
            self.nodeFH = open(self.nodes_file_name, "w")
            self.nodeFH.write(self.delimiter.join(self.node_columns) + "\n")

        if edge_properties: # Make edge file
            self.edge_columns = TSVWriter._order_columns(edge_properties, "edge")
            self.edges_file_name = Path(self.dirname if self.dirname else "", f"{self.basename}_edges.tsv")
            self.edgeFH = open(self.edges_file_name, "w")
            self.edgeFH.write(self.delimiter.join(self.edge_columns) + "\n")

    def write(self, entities: Iterable) -> None:
        """Write an entities object to separate node and edge .tsv files"""

        nodes, edges = self.converter.convert(entities)

        if nodes:
            for node in nodes:
                self.write_row(node, record_type="node")

        if edges:
            for edge in edges:
                edge = self._apply_sssom(edge) if hasattr(self, "sssom_df") else edge
                self.write_row(edge, record_type="edge")

    def write_row(self, record: Dict, record_type: Literal["node", "edge"]) -> None:
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
        
        if hasattr(self, 'nodeFH'):
            self.nodeFH.close()
        if hasattr(self, 'edgeFH'):
            self.edgeFH.close()

    def _apply_sssom(self, entity: dict) -> dict:
        """Apply SSSOM mappings to a node or edge record."""
        print(entity)
        if entity["subject"] in self.sssom_df["subject_id"].values:
            entity["original_subject"] = entity["subject"]
            entity["subject"] = self.sssom_df.loc[self.sssom_df["subject_id"] == entity["subject"]]["object_id"].values[0]

        if entity["object"] in self.sssom_df["subject_id"].values:
            entity["original_object"] = entity["object"]
            entity["object"] = self.sssom_df.loc[self.sssom_df["subject_id"] == entity["object"]]["object_id"].values[0]

        if entity["subject"] in self.sssom_df["object_id"].values:
            entity["original_subject"] = entity["subject"]
            entity["subject"] = self.sssom_df.loc[self.sssom_df["object_id"] == entity["subject"]]["subject_id"].values[0]

        if entity["object"] in self.sssom_df["object_id"].values:
            entity["original_object"] = entity["object"]
            entity["object"] = self.sssom_df.loc[self.sssom_df["object_id"] == entity["object"]]["subject_id"].values[0]

        return entity


    @staticmethod
    def _order_columns(cols: Set, record_type: Literal['node', 'edge']) -> OrderedSet:
        """Arrange node or edge columns in a defined order.
        
        Args:
            cols: Set - A set with elements in any order
        
        Returns:
            OrderedSet - A set with elements in a defined order
        """
        if record_type == 'node':
            core_columns = OrderedSet(
                ["id", "category", "name", "description", "xref", "provided_by", "synonym"]
            )
        elif record_type == 'edge':
            core_columns = OrderedSet(
                ["id", "subject", "predicate", "object", "category", "provided_by"]
            )
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
