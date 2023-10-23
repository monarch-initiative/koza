"""
source config data class
map config data class
"""

import os
import tarfile
import zipfile
from dataclasses import field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Union, Literal
import yaml

from loguru import logger
from pydantic import StrictFloat, StrictInt, StrictStr
from pydantic.dataclasses import dataclass
from sssom.parsers import parse_sssom_table
from sssom.util import filter_prefixes, merge_msdf

from koza.model.config.pydantic_config import PydanticConfig


class FilterCode(str, Enum):
    """Enum for filter codes (ex. gt = greater than)

    This should be aligned with https://docs.python.org/3/library/operator.html
    """

    gt = "gt"
    ge = "ge"
    lt = "lt"
    lte = "le"
    eq = "eq"
    ne = "ne"
    inlist = "in"


class FilterInclusion(str, Enum):
    """Enum for filter inclusion/exclusion"""

    include = "include"
    exclude = "exclude"


class FieldType(str, Enum):
    """Enum for field types"""

    str = "str"
    int = "int"
    float = "float"


class FormatType(str, Enum):
    """Enum for supported file types"""

    csv = "csv"
    jsonl = "jsonl"
    json = "json"
    yaml = "yaml"
    xml = "xml"  # TODO


class HeaderMode(str, Enum):
    """Enum for supported header modes in addition to an index based lookup"""

    infer = "infer"
    none = "none"


class MapErrorEnum(str, Enum):
    """Enum for how to handle key errors in map files"""

    warning = "warning"
    error = "error"


class OutputFormat(str, Enum):
    """
    Output formats
    """

    tsv = "tsv"
    jsonl = "jsonl"
    kgx = "kgx"


class StandardFormat(str, Enum):
    gpi = "gpi"
    bgi = "bgi"
    oban = "oban"


class TransformMode(str, Enum):
    """
    Configures how an external transform file is processed
    flat uses importlib and watches for a StopIteration
    exception, loop runs the code once and expects that
    a for loop is being used to iterate over a file
    """

    flat = "flat"
    loop = "loop"


@dataclass(frozen=True)
class ColumnFilter:
    column: str
    inclusion: FilterInclusion
    filter_code: FilterCode
    value: Union[StrictInt, StrictFloat, StrictStr, List[Union[StrictInt, StrictFloat, StrictStr]]]


@dataclass(frozen=True)
class DatasetDescription:
    """
    These options should be treated as being in alpha, as we need
    to align with various efforts (hcls, translator infores)

    These currently do not serve a purpose in koza other
    than documentation
    """

    id: str = None  # TODO constrain to a curie?
    name: str = None  # If empty use source name
    ingest_title: str = None  # Map to biolink name
    ingest_url: str = None  # Maps to biolink iri
    description: str = None
    source: str = None
    provided_by: str = None
    license: str = None
    rights: str = None


@dataclass()
class SSSOMConfig:
    """SSSOM config options

    Attributes:
        files: List of SSSOM files to use
        filter_prefixes: Optional list of prefixes to filter by
        subject_target_prefixes: Optional list of prefixes to use for subject mapping
        object_target_prefixes: Optional list of prefixes to use for object mapping

    """

    files: List[Union[str, Path]] = field(default_factory=list)
    filter_prefixes: List[str] = field(default_factory=list)
    subject_target_prefixes: List[str] = field(default_factory=list)
    object_target_prefixes: List[str] = field(default_factory=list)

    predicates = {"exact": ["skos:exactMatch"], "narrow": ["skos:narrowMatch"], "broad": ["skos:broadMatch"]}

    def __post_init_post_parse__(self):
        logger.debug("Building SSSOM Dataframe...")
        self.df = self._merge_and_filter_sssom()
        logger.debug("Building SSSOM Lookup Table...")
        self.lut = self._build_sssom_lut()

    def apply_mapping(self, entity: dict) -> dict:
        """Apply SSSOM mappings to an edge record."""

        if self._has_mapping(entity["subject"], self.subject_target_prefixes):
            entity["original_subject"] = entity["subject"]
            entity["subject"] = self._get_mapping(entity["subject"], self.subject_target_prefixes)

        if self._has_mapping(entity["object"], self.object_target_prefixes):
            entity["original_object"] = entity["object"]
            entity["object"] = self._get_mapping(entity["object"], self.object_target_prefixes)

        return entity

    def _merge_and_filter_sssom(self):
        mapping_sets = []
        for file in self.files:
            msdf = parse_sssom_table(file)
            mapping_sets.append(msdf)
        new_msdf = merge_msdf(*mapping_sets)
        filters = (self.subject_target_prefixes + self.object_target_prefixes) + list(
            set(self.filter_prefixes) - set(self.subject_target_prefixes) - set(self.object_target_prefixes)
        )
        logger.debug(f"Filtering SSSOM by {filters}")
        new_msdf = filter_prefixes(
            df=new_msdf.df, filter_prefixes=filters, require_all_prefixes=False, features=new_msdf.df.columns
        )

        return new_msdf

    def _build_sssom_lut(self) -> Dict:
        """Build a lookup table from SSSOM mapping dataframe."""
        sssom_lut = {}
        for _, row in self.df.iterrows():
            subject_id = row["subject_id"]
            object_id = row["object_id"]
            predicate = row["predicate_id"]
            sssom_lut = self._set_mapping(subject_id, object_id, predicate, match="exact", lut=sssom_lut)
            # sssom_lut = self._set_mapping(subject_id, object_id, predicate, match='broad', lut=sssom_lut)
            # sssom_lut = self._set_mapping(object_id, subject_id, predicate, match='narrow', lut=sssom_lut)
        return sssom_lut

    def _has_match(self, predicate, match: Literal["exact", "narrow", "broad"]):
        """Check if a predicate has a match."""
        if match == "exact":
            return predicate in self.predicates["exact"]
        if match == "narrow":
            # return predicate in self.predicates["narrow"] or predicate in self.predicates["exact"]
            logger.warning("Narrow match not yet implemented")
            return False
        if match == "broad":
            # return predicate in self.predicates["broad"] or predicate in self.predicates["exact"]
            logger.warning("Broad match not yet implemented")
            return False

    def _has_mapping(self, id, target_prefixes=None):
        """Check if an ID has a mapping."""
        if target_prefixes is None:
            return id in self.lut
        else:
            if id not in self.lut:
                return False
            for target_prefix in target_prefixes:
                if target_prefix in self.lut[id]:
                    return True
            return False # No mapping found

    def _get_mapping(self, id, target_prefixes):
        """Get the mapping for an ID."""
        for target_prefix in target_prefixes:
            if target_prefix in self.lut[id]:
                return self.lut[id][target_prefix]
        raise KeyError(f"Could not find mapping for {id} in {target_prefixes}: {self.lut[id]}")

    def _set_mapping(
        self, original_id, mapped_id, predicate, match: Literal["exact", "narrow", "broad"], lut: Dict[str, dict]
    ):
        """Set a mapping for an ID."""
        original_prefix = original_id.split(":")[0]
        mapped_prefix = mapped_id.split(":")[0]
        target_prefixes = self.subject_target_prefixes + self.object_target_prefixes
        if (
            original_prefix in self.filter_prefixes or len(self.filter_prefixes) == 0
        ) and mapped_prefix in target_prefixes:
            if original_id not in lut:
                lut[original_id] = {}
            if mapped_prefix in lut[original_id]:
                logger.warning(f"Duplicate mapping for {original_id} to {mapped_prefix}")
            elif self._has_match(predicate, match):
                lut[original_id][mapped_prefix] = mapped_id
            else:
                pass  # do something else
        return lut


@dataclass(config=PydanticConfig)
class SourceConfig:
    """
    Source config data class

    Parameters
    ----------
    name: str (required) - name of the source
    files: List[str] (required) - list of files to process
    file_archive: str (optional) - path to a file archive containing files to process
    format: FormatType (optional) - format of the data file(s)
    sssom_config: SSSOMConfig (optional) - SSSOM config options
    metadata: DatasetDescription (optional) - metadata for the source
    columns: List[str] (optional) - list of columns to include
    required_properties: List[str] (optional) - list of properties which must be in json data files
    delimiter: str (optional) - delimiter for csv files
    header_delimiter: str (optional) - delimiter for header in csv files
    header: int (optional) - header row index
    comment_char: str (optional) - comment character for csv files
    skip_blank_lines: bool (optional) - skip blank lines in csv files
    filters: List[ColumnFilter] (optional) - list of filters to apply
    json_path: List[str] (optional) - path within JSON object containing data to process
    transform_code: str (optional) - path to a python file to transform the data
    transform_mode: TransformMode (optional) - how to process the transform file
    global_table: str (optional) - path to a global table file
    local_table: str (optional) - path to a local table file
    """

    name: str
    files: List[Union[str, Path]]
    file_archive: Union[str, Path] = None
    format: FormatType = FormatType.csv
    sssom_config: SSSOMConfig = None
    columns: List[Union[str, Dict[str, FieldType]]] = None
    required_properties: List[str] = None
    metadata: Union[DatasetDescription, str] = None
    delimiter: str = None
    header: Union[int, HeaderMode] = HeaderMode.infer
    header_delimiter: str = None
    comment_char: str = "#"
    skip_blank_lines: bool = True
    filters: List[ColumnFilter] = field(default_factory=list)
    json_path: List[Union[StrictStr, StrictInt]] = None
    transform_code: str = None
    transform_mode: TransformMode = TransformMode.flat
    global_table: Union[str, Dict] = None
    local_table: Union[str, Dict] = None

    def extract_archive(self):
        archive_path = Path(self.file_archive).parent  # .absolute()
        if self.file_archive.endswith(".tar.gz") or self.file_archive.endswith(".tar"):
            with tarfile.open(self.file_archive) as archive:
                archive.extractall(archive_path)
        elif self.file_archive.endswith(".zip"):
            with zipfile.ZipFile(self.file_archive, "r") as archive:
                archive.extractall(archive_path)
        else:
            raise ValueError("Error extracting archive. Supported archive types: .tar.gz, .zip")
        files = [os.path.join(archive_path, file) for file in self.files]
        return files

    def __post_init_post_parse__(self):
        """
        TO DO figure out why we're using object.__setattr__(self, ...)
            here and document it.
            Is this a workaround for a pydantic bug?
        """
        if self.file_archive:
            files = self.extract_archive()
        else:
            files = self.files

        files_as_paths: List[Path] = []
        for file in files:
            if isinstance(file, str):
                files_as_paths.append(Path(file))
            else:
                files_as_paths.append(file)
        object.__setattr__(self, "files", files_as_paths)
        # self.files = files_as_paths <---- is this equivalent to the above?

        if self.metadata and isinstance(self.metadata, str):
            # If this looks like a file path attempt to load it from the yaml
            # TODO enforce that this is imported via an include?
            # See https://github.com/monarch-initiative/koza/issues/46
            try:
                with open(self.metadata, "r") as meta:
                    object.__setattr__(self, "metadata", DatasetDescription(**yaml.safe_load(meta)))
            except Exception as e:
                # TODO check for more explicit exceptions
                raise ValueError(f"Unable to load metadata from {self.metadata}: {e}")

        if self.delimiter in ["tab", "\\t"]:
            object.__setattr__(self, "delimiter", "\t")

        filtered_columns = [column_filter.column for column_filter in self.filters]

        all_columns = []
        if self.columns:
            all_columns = [next(iter(column)) if isinstance(column, Dict) else column for column in self.columns]

        if self.header == HeaderMode.none and not self.columns:
            raise ValueError(
                f"there is no header and columns have not been supplied\n"
                f"configure the 'columns' field or set header to the 0-based"
                "index in which it appears in the file, or set this value to"
                "'infer'"
            )

        for column in filtered_columns:
            if column not in all_columns:
                raise (ValueError(f"Filter column {column} not in column list"))

        for column_filter in self.filters:
            if column_filter.filter_code in ["lt", "gt", "lte", "gte"]:
                # TODO determine if this should raise an exception
                # or instead try to type coerce the string to a float
                # type coercion is probably the best thing to do here
                if not isinstance(column_filter.value, (int, float)):
                    raise ValueError(f"Filter value must be int or float for operator {column_filter.filter_code}")
            elif column_filter.filter_code == "eq":
                if not isinstance(column_filter.value, (str, int, float)):
                    raise ValueError(
                        f"Filter value must be string, int or float for operator {column_filter.filter_code}"
                    )
            elif column_filter.filter_code == "in":
                if not isinstance(column_filter.value, List):
                    raise ValueError(f"Filter value must be List for operator {column_filter.filter_code}")

        if self.format == FormatType.csv and self.required_properties:
            raise ValueError(
                "CSV specified but required properties have been configured\n"
                "either set format to jsonl or change properties to columns in the config"
            )

        if self.columns and self.format != FormatType.csv:
            raise ValueError(
                "columns have been configured but format is not csv\n"
                "either set format to csv or change columns to properties in the config"
            )

        if self.json_path and self.format != FormatType.json:
            raise ValueError(
                "iterate_over has been configured but format is not json\n"
                "either set format to json or remove iterate_over in the configuration"
            )

        if self.columns:
            _field_type_map = {}
            for field in self.columns:
                if isinstance(field, str):
                    _field_type_map[field] = FieldType.str
                else:
                    if len(field) != 1:
                        # TODO expand this exception msg
                        raise ValueError("Field type map contains more than one key")
                    for key, val in field.items():
                        _field_type_map[key] = val
            object.__setattr__(self, "_field_type_map", _field_type_map)

    @property
    def field_type_map(self):
        return self._field_type_map


@dataclass(config=PydanticConfig)
class PrimaryFileConfig(SourceConfig):
    """
    node_properties and edge_properties are used for configuring
    the KGX writer
    """

    node_properties: List[str] = None
    edge_properties: List[str] = None
    depends_on: List[str] = field(default_factory=list)
    on_map_failure: MapErrorEnum = MapErrorEnum.warning


@dataclass(config=PydanticConfig)
class MapFileConfig(SourceConfig):
    key: str = None
    values: List[str] = None
    curie_prefix: str = None
    add_curie_prefix_to_columns: List[str] = None
