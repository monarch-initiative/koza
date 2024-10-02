import json
from pathlib import Path
from typing import Union, List
from linkml_runtime import SchemaView
from linkml_runtime.utils.formatutils import camelcase, uncamelcase, underscore

from koza.io.utils import build_export_row
from koza.io.writer.writer import KozaWriter
from koza.model.config.source_config import OutputFormat
from koza.model.config.sssom_config import SSSOMConfig


class LinkMLWriter(KozaWriter):

    def __init__(self,
                 output_dir: Union[str,Path],
                 filename: str,
                 schemaview: SchemaView,
                 class_names: List[str],
                 sssom_config: SSSOMConfig = None
                 ):
        self.fh = open(Path(output_dir, filename), 'w')
        self.sv = schemaview
        self.slots = self.get_slot_names(class_names)
        self.sssom_config = sssom_config
        self.rows = []
        self.used_slots = set()
        self.output_format = self.get_output_format(filename)
        self.delimiter = "\t"
        # TODO: pass delimiter and list_delimiter as arguments
        self.delimiter = "\t"
        self.list_delimiter = "|"



    def write(self, record):
        #TODO: add assertion about the class of record?
        export_row = build_export_row(record.dict(), list_delimiter=self.list_delimiter)
        self.rows.append(export_row)
        self.used_slots.update(export_row.keys())

    def finalize(self):
        # todo: sort the slots in an external function that looks at the schema, applies sensible defaults about identifier, type designator & label slots , etc
        ordered_slots = self.sort_slots(self.used_slots)
        if (self.output_format == OutputFormat.tsv):
            # write the header
            self.fh.write(self.delimiter.join(ordered_slots) + "\n")
        for export_row in self.rows:
            if self.output_format == OutputFormat.tsv:
                ordered_values = [export_row[slot] if slot in export_row else None for slot in ordered_slots]
                self.fh.write(self.delimiter.join(ordered_values) + "\n")
            elif self.output_format == OutputFormat.jsonl:
                self.fh.write(json.dumps(export_row) + "\n")

        self.fh.close()

    def sort_slots(self, slots: List[str]) -> List[str]:
        # TODO: generalize this a little more, at least biolink vs sssom, also try using rank
        # sort the slots with a specific order for some slots and the rest alphabetically
        specific_order = ['id', 'category', 'subject', 'predicate', 'object']
        ordered_slots = [slot for slot in specific_order if slot in slots]
        remaining_slots = sorted(set(slots) - set(specific_order))
        return ordered_slots + remaining_slots

    def get_class(self, cn: str) -> str:
        """ Get class from SchemaView being flexible about how the clas name is formatted"""
        class_definition = self.sv.get_class(cn)
        if class_definition is None:
            class_definition = self.sv.get_class(camelcase(cn))
        if class_definition is None:
            class_definition = self.sv.get_class(uncamelcase(cn))
        if class_definition is None:
            raise ValueError(f"Class {cn} not found in schema")
        return class_definition

    def get_slot_names(self, class_names: List[str]) -> List[str]:
        sv = self.sv
        slots = set()
        for cn in class_names:
            class_definition = self.get_class(cn)
            for slot in sv.class_induced_slots(class_definition.name):
                slots.add(slot.name)
        # convert to underscore
        return [underscore(slot) for slot in slots]

    def get_output_format(self, filename: str) -> OutputFormat:
        return OutputFormat(Path(filename).suffix[1:])
