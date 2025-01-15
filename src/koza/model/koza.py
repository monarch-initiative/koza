from dataclasses import field
from typing import Optional, Union

import yaml
from ordered_set import OrderedSet
from pydantic.dataclasses import dataclass

from koza.model.config.pydantic_config import PYDANTIC_CONFIG
from koza.model.formats import InputFormat
from koza.model.reader import CSVReaderConfig, ReaderConfig
from koza.model.transform import TransformConfig
from koza.model.writer import WriterConfig

__all__ = ("DatasetDescription", "KozaConfig")


@dataclass(frozen=True)
class DatasetDescription:
    """
    These options should be treated as being in alpha, as we need
    to align with various efforts (hcls, translator infores)

    These currently do not serve a purpose in koza other than documentation
    """

    # id: Optional[str] = None          # Can uncomment when we have a standard
    name: Optional[str] = None  # If empty use source name
    ingest_title: Optional[str] = None  # Title of source of data, map to biolink name
    ingest_url: Optional[str] = None  # URL to source of data, maps to biolink iri
    description: Optional[str] = None  # Description of the data/ingest
    # source: Optional[str] = None      # Possibly replaced with provided_by
    provided_by: Optional[str] = None  # <data source>_<type_of_ingest>, ex. hpoa_gene_to_disease
    # license: Optional[str] = None     # Possibly redundant, same as rights
    rights: Optional[str] = None  # License information for the data source


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class KozaConfig:
    name: str
    reader: ReaderConfig = field(default_factory=CSVReaderConfig)
    transform: TransformConfig = field(default_factory=TransformConfig)
    writer: WriterConfig = field(default_factory=WriterConfig)
    metadata: Optional[Union[DatasetDescription, str]] = None

    def __post_init__(self):
        # If metadata looks like a file path attempt to load it from the yaml
        if self.metadata and isinstance(self.metadata, str):
            try:
                with open(self.metadata, "r") as meta:
                    object.__setattr__(self, "metadata", DatasetDescription(**yaml.safe_load(meta)))
            except Exception as e:
                raise ValueError(f"Unable to load metadata from {self.metadata}: {e}") from e

        if self.reader.format == InputFormat.csv and self.reader.columns is not None:
            filtered_columns = OrderedSet([column_filter.column for column_filter in self.transform.filters])
            all_columns = OrderedSet(
                [column if isinstance(column, str) else list(column.keys())[0] for column in self.reader.columns]
            )
            extra_filtered_columns = filtered_columns - all_columns
            if extra_filtered_columns:
                quote = "'"
                raise ValueError(
                    "One or more filter columns not present in designated CSV columns:"
                    f" {', '.join([f'{quote}{c}{quote}' for c in extra_filtered_columns])}"
                )
