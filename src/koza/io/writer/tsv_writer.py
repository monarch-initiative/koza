#### TSV Writer ####
# NOTE - May want to rename to KGXWriter at some point, if we develop writers for other models non biolink/kgx specific

from pathlib import Path
from typing import Dict, Iterable, List, Literal, Set

from ordered_set import OrderedSet
from sssom.parsers import parse_sssom_table
from sssom.util import filter_prefixes

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
            self.sssom_tables = []
            for file in sssom_config.files:
                table = parse_sssom_table(file)
                table = filter_prefixes(table, self.sssom_prefixes)
                self.sssom_tables.append(table)         

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
                self.write_row(node, "node")

        if edges:
            for edge in edges:
                self.write_row(self._apply_mapping(edge), "edge")

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

    def _apply_mappings(self, edge):
        """
        Apply SSSOM mappings to edges.

        Args:
            edges (pandas.DataFrame): DataFrame of edges.
            mapping (pandas.DataFrame): DataFrame of SSSOM mappings.

        Returns:
            None
        """
        # edges.rename(columns={'subject':'original_subject'}, inplace=True)
        # subject_mapping = mapping.rename(columns={'subject_id':'subject'})
        # subject_mapping = subject_mapping[["subject","object_id"]]
        # edges = edges.merge(subject_mapping, how='left', left_on='original_subject', right_on='object_id').drop(['object_id'],axis=1)
        # edges['subject'] = np.where(edges.subject.isnull(), edges.original_subject, edges.subject)
        # edges['original_subject'] = np.where(edges.subject == edges.original_subject, None, edges.original_subject)

        # edges.rename(columns={'object':'original_object'}, inplace=True)
        # object_mapping = mapping.rename(columns={'subject_id':'object'})
        # object_mapping = object_mapping[["object", "object_id"]]
        # edges = edges.merge(object_mapping, how='left', left_on='original_object', right_on='object_id').drop(['object_id'],axis=1)
        # edges['object'] = np.where(edges.object.isnull(), edges.original_object, edges.object)
        # edges['original_object'] = np.where(edges.object == edges.original_object, None, edges.original_object)

        # return edges
        pass

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
