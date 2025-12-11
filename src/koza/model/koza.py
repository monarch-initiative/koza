from dataclasses import field

import yaml
from pydantic.dataclasses import dataclass

from koza.model.config.pydantic_config import PYDANTIC_CONFIG
from koza.model.reader import ReaderConfig
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
    name: str | None = None  # If empty use source name
    ingest_title: str | None = None  # Title of source of data, map to biolink name
    ingest_url: str | None = None  # URL to source of data, maps to biolink iri
    description: str | None = None  # Description of the data/ingest
    # source: Optional[str] = None      # Possibly replaced with provided_by
    provided_by: str | None = None  # <data source>_<type_of_ingest>, ex. hpoa_gene_to_disease
    # license: Optional[str] = None     # Possibly redundant, same as rights
    rights: str | None = None  # License information for the data source


@dataclass(frozen=True)
class TaggedReaderConfig:
    tag: str | None
    reader: ReaderConfig


@dataclass(config=PYDANTIC_CONFIG, frozen=True)
class KozaConfig:
    name: str
    reader: ReaderConfig | None = None
    readers: dict[str, ReaderConfig] | None = None
    transform: TransformConfig = field(default_factory=TransformConfig)
    writer: WriterConfig = field(default_factory=WriterConfig)
    metadata: DatasetDescription | str | None = None

    def get_readers(self) -> list[TaggedReaderConfig]:
        if self.reader is not None:
            return [TaggedReaderConfig(None, self.reader)]
        elif self.readers is not None:
            return [TaggedReaderConfig(tag, reader) for tag, reader in self.readers.items()]
        else:
            return []

    def __post_init__(self):
        if self.reader is not None and self.readers is not None:
            raise ValueError("Can only define one of `reader` or `readers`")
        # If metadata looks like a file path attempt to load it from the yaml
        if self.metadata and isinstance(self.metadata, str):
            try:
                with open(self.metadata) as meta:
                    object.__setattr__(self, "metadata", DatasetDescription(**yaml.safe_load(meta)))
            except Exception as e:
                raise ValueError(f"Unable to load metadata from {self.metadata}: {e}") from e
