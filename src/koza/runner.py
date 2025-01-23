import importlib
import sys
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, Iterator, Optional

import yaml
from loguru import logger
from mergedeep import merge
from typing_extensions import assert_never

from koza.io.writer.jsonl_writer import JSONLWriter
from koza.io.writer.passthrough_writer import PassthroughWriter
from koza.io.writer.tsv_writer import TSVWriter
from koza.io.writer.writer import KozaWriter
from koza.io.yaml_loader import UniqueIncludeLoader
from koza.model.formats import OutputFormat
from koza.model.koza import KozaConfig
from koza.model.source import Source
from koza.model.transform import MapErrorEnum
from koza.utils.exceptions import MapItemException, NoTransformException

Record = Dict[str, Any]
Mappings = dict[str, dict[str, dict[str, str]]]


def is_function(obj: object, attr: str):
    return hasattr(obj, attr) and callable(getattr(obj, attr))


@dataclass(kw_only=True)
class KozaTransform(ABC):
    extra_fields: Dict[str, Any]
    writer: KozaWriter
    mappings: Mappings
    on_map_failure: MapErrorEnum = MapErrorEnum.warning

    @property
    @abstractmethod
    def data(self) -> Iterator[Record]: ...

    def write(self, *records: Record, writer: Optional[str] = None) -> None:
        """Write a series of records to a writer.

        The writer argument specifies the specific writer to write to (named
        writers not yet implemented)
        """
        self.writer.write(records)

    def lookup(self, name: str, map_column: str, map_name: Optional[str] = None) -> str:
        """Look up a term in the configured mappings.

        In the one argument form:

            koza.lookup("name")

        It will look for the first match for "name" in the configured mappings.
        The first mapping will have precendence over any proceeding ones.

        If a map name is provided, only that named mapping will be used:

            koza.lookup("name", map_name="mapping_a")

        """
        try:
            if map_name:
                mapping = self.mappings.get(map_name, None)
                if mapping is None:
                    raise MapItemException(f"Map {map_name} does not exist")

                values = mapping.get(name, None)
                if values is None:
                    raise MapItemException(f"No record for {name} in map {map_name}")

                mapped_value = values.get(map_column, None)
                if mapped_value is None:
                    raise MapItemException(f"No record for {name} in column {map_column} in {map_name}")

                return mapped_value
            else:
                for mapping in self.mappings.values():
                    values = mapping.get(name, None)
                    if values is None:
                        raise MapItemException(f"No record for {name} in map {map_name}")

                    mapped_value = values.get(map_column, None)
                    if mapped_value is None:
                        raise MapItemException(f"No record for {name} in column {map_column} in {map_name}")

                    return mapped_value
                else:
                    raise MapItemException(f"No record found in any mapping for {name} in column {map_column}")
        except MapItemException as e:
            match self.on_map_failure:
                case MapErrorEnum.error:
                    raise e
                case MapErrorEnum.warning:
                    return name
                case _:
                    assert_never(self.on_map_failure)

    def log(self, msg: str, level: str = "info") -> None:
        """Log a message."""
        logger.log(level, msg)

    @property
    @abstractmethod
    def current_reader(self) -> str:
        """Returns the reader for the last row read.

        Useful for getting the filename of the file that a row was read from:

            for row in koza.iter_rows():
                filename = koza.current_reader.filename
        """
        ...


@dataclass(kw_only=True)
class SingleTransform(KozaTransform):
    _data: Iterator[Record]

    @property
    def data(self):
        return self._data

    @property
    def current_reader(self):
        raise NotImplementedError()


@dataclass(kw_only=True)
class SerialTransform(KozaTransform):
    @property
    def data(self):
        raise NotImplementedError()

    @property
    def current_reader(self):
        raise NotImplementedError()


class KozaRunner:
    def __init__(
        self,
        data: Iterator[Record],
        writer: KozaWriter,
        mapping_filenames: Optional[list[str]] = None,
        extra_transform_fields: Optional[dict[str, Any]] = None,
        transform_record: Optional[Callable[[KozaTransform, Record], None]] = None,
        transform: Optional[Callable[[KozaTransform], None]] = None,
    ):
        self.data = data
        self.writer = writer
        self.mapping_filenames = mapping_filenames or []
        self.transform_record = transform_record
        self.transform = transform
        self.extra_transform_fields = extra_transform_fields or {}

    def run_single(self):
        fn = self.transform

        if fn is None:
            raise NoTransformException("Can only be run when `transform` is defined")

        mappings = self.load_mappings()

        logger.info("Running single transform")
        transform = SingleTransform(
            _data=self.data,
            mappings=mappings,
            writer=self.writer,
            extra_fields=self.extra_transform_fields,
        )
        fn(transform)

    def run_serial(self):
        fn = self.transform_record

        if fn is None:
            raise NoTransformException("Can only be run when `transform_record` is defined")

        mappings = self.load_mappings()

        logger.info("Running serial transform")
        transform = SerialTransform(
            mappings=mappings,
            writer=self.writer,
            extra_fields=self.extra_transform_fields,
        )
        for item in self.data:
            fn(transform, item)

    def run(self):
        if callable(self.transform) and callable(self.transform_record):
            raise ValueError("Can only define one of `transform` or `transform_record`")
        elif callable(self.transform):
            self.run_single()
        elif callable(self.transform_record):
            self.run_serial()
        else:
            raise NoTransformException("Must define one of `transform` or `transform_record`")

        self.writer.finalize()

    def load_mappings(self):
        mappings: Mappings = {}

        if self.mapping_filenames:
            logger.info("Loading mappings")

        for mapping_config_filename in self.mapping_filenames:
            # Check if a transform has been defined for the mapping
            config, map_runner = KozaRunner.from_config_file(
                mapping_config_filename,
                output_format=OutputFormat.passthrough,
            )
            try:
                map_runner.run()
                data = map_runner.writer.result()
                assert isinstance(data, list)
            except NoTransformException:
                data = map_runner.data

            mapping_entry: dict[str, dict[str, str]] = {}
            key_column: Optional[str] = map_runner.extra_transform_fields.get("key", None)
            value_columns: Optional[list[str]] = map_runner.extra_transform_fields.get("values", None)

            if key_column is None:
                raise ValueError(f"Must define transform mapping key column in configuration for {config.name}")

            if not isinstance(value_columns, list):
                raise ValueError(
                    "Must define a list of transform mapping value columns in configuration for {config.name}"
                )

            for row in data:
                item_key = row[key_column]

                mapping_entry[str(item_key)] = {
                    key: value
                    for key, value in row.items()
                    if key in value_columns
                    #
                }

            mappings[config.name] = mapping_entry

        if self.mapping_filenames:
            logger.info("Completed loading mappings")

        return mappings

    @classmethod
    def from_config(
        cls,
        config: KozaConfig,
        output_dir: str = "",
        row_limit: int = 0,
        show_progress: bool = False,
    ):
        module_name: Optional[str] = None
        transform_module: Optional[ModuleType] = None

        if config.transform.code:
            transform_code_path = Path(config.transform.code)
            parent_path = transform_code_path.absolute().parent
            module_name = transform_code_path.stem
            logger.debug(f"Adding `{parent_path}` to system path to load transform module")
            sys.path.append(str(parent_path))
            # FIXME: Remove this from sys.path
        elif config.transform.module:
            module_name = config.transform.module

        if module_name:
            logger.debug(f"Loading module `{module_name}`")
            transform_module = importlib.import_module(module_name)

        transform = getattr(transform_module, "transform", None)
        if transform:
            logger.debug(f"Found transform function `{module_name}.transform`")
        transform_record = getattr(transform_module, "transform_record", None)
        if transform_record:
            logger.debug(f"Found transform function `{module_name}.transform_record`")
        source = Source(config, row_limit, show_progress)

        writer: Optional[KozaWriter] = None

        if config.writer.format == OutputFormat.tsv:
            writer = TSVWriter(output_dir=output_dir, source_name=config.name, config=config.writer)
        elif config.writer.format == OutputFormat.jsonl:
            writer = JSONLWriter(output_dir=output_dir, source_name=config.name, config=config.writer)
        elif config.writer.format == OutputFormat.passthrough:
            writer = PassthroughWriter()

        if writer is None:
            raise ValueError("No writer defined")

        return cls(
            data=iter(source),
            writer=writer,
            mapping_filenames=config.transform.mappings,
            extra_transform_fields=config.transform.extra_fields,
            transform=transform,
            transform_record=transform_record,
        )

    @classmethod
    def from_config_file(
        cls,
        config_filename: str,
        output_dir: str = "",
        output_format: Optional[OutputFormat] = None,
        row_limit: int = 0,
        show_progress: bool = False,
        overrides: Optional[dict] = None,
    ):
        transform_code_path: Optional[Path] = None
        config_path = Path(config_filename)

        logger.info(f"Loading configuration from `{config_filename}`")

        with config_path.open("r") as fh:
            config_dict = yaml.load(fh, Loader=UniqueIncludeLoader)  # noqa: S506
            config = KozaConfig(**config_dict)

        if not config.transform.code and not config.transform.module:
            # If config file is named:
            #   /path/to/transform_name.yaml
            # then look for a transform at
            #   /path/to/transform_name.py
            mirrored_path = config_path.parent / f"{config_path.stem}.py"

            # Otherwise, look for a file named transform.py in the same directory
            transform_literal_path = config_path.parent / "transform.py"

            if mirrored_path.exists():
                transform_code_path = mirrored_path
            elif transform_literal_path.exists():
                transform_code_path = transform_literal_path

            if transform_code_path:
                logger.debug(f"Using transform code from `{mirrored_path}`")

        # Override any necessary fields
        config_dict = asdict(config)
        _overrides = {}
        if output_format is not None:
            _overrides["writer"] = {
                "format": output_format,
            }
        if transform_code_path is not None:
            _overrides["transform"] = {
                "code": str(transform_code_path),
            }
        config_dict = merge(config_dict, _overrides, overrides or {})
        config = KozaConfig(**config_dict)

        return config, cls.from_config(config, output_dir=output_dir, row_limit=row_limit,
                                       show_progress=show_progress)
