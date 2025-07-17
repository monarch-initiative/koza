import importlib
import sys
from collections.abc import Callable, Iterator
from dataclasses import asdict
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar

import yaml
from loguru import logger
from mergedeep import merge

from koza import decorators
from koza.io.writer.jsonl_writer import JSONLWriter
from koza.io.writer.passthrough_writer import PassthroughWriter
from koza.io.writer.tsv_writer import TSVWriter
from koza.io.writer.writer import KozaWriter
from koza.io.yaml_loader import UniqueIncludeLoader
from koza.model.formats import OutputFormat
from koza.model.koza import KozaConfig
from koza.model.source import Source
from koza.transform import KozaTransform, Mappings, Record, SerialTransform, SingleTransform
from koza.utils.exceptions import NoTransformException

T = TypeVar("T")


def get_instances(cls: type[T], from_list: list[Any]) -> list[T]:
    ret: list[T] = []
    for item in from_list:
        if isinstance(item, cls):
            ret.append(item)
    return ret


class KozaRunner:
    def __init__(
        self,
        data: Iterator[Record],
        writer: KozaWriter,
        base_directory: Path | None = None,
        mapping_filenames: list[str] | None = None,
        extra_transform_fields: dict[str, Any] | None = None,
        transform_record: Callable[[KozaTransform, Record], None] | None = None,
        transform: Callable[[KozaTransform], None] | None = None,
        on_data_begin: Callable[[KozaTransform], None] | None = None,
        on_data_end: Callable[[KozaTransform], None] | None = None,
    ):
        self.data = data
        self.writer = writer
        self.mapping_filenames = mapping_filenames or []
        self.transform_record = transform_record
        self.transform = transform
        self.extra_transform_fields = extra_transform_fields or {}
        self.base_directory = base_directory
        self.on_data_begin = on_data_begin
        self.on_data_end = on_data_end

    def run(self):
        mappings = self.load_mappings()

        if callable(self.transform) and callable(self.transform_record):
            raise ValueError("Can only define one of `transform` or `transform_record`")
        elif callable(self.transform):
            logger.info("Running single transform")
            transform = SingleTransform(
                _data=self.data,
                mappings=mappings,
                writer=self.writer,
                extra_fields=self.extra_transform_fields,
            )
            if callable(self.on_data_begin):
                self.on_data_begin(transform)

            self.transform(transform)
        elif callable(self.transform_record):
            logger.info("Running serial transform")
            transform = SerialTransform(
                mappings=mappings,
                writer=self.writer,
                extra_fields=self.extra_transform_fields,
            )
            if callable(self.on_data_begin):
                self.on_data_begin(transform)

            for item in self.data:
                self.transform_record(transform, item)
        else:
            raise NoTransformException("Must define one of `transform` or `transform_record`")

        if callable(self.on_data_end):
            self.on_data_end(transform)

        self.writer.finalize()

        return self.writer

    def load_mappings(self):
        mappings: Mappings = {}

        if self.mapping_filenames:
            logger.info("Loading mappings")

        for mapping_config_filename in self.mapping_filenames:
            mapping_config = Path(mapping_config_filename)
            if not mapping_config.is_absolute():
                if self.base_directory is None:
                    raise ValueError("Cannot load config maps without a `base_directory` set.")
                mapping_config = self.base_directory / mapping_config

            # Check if a transform has been defined for the mapping
            config, map_runner = KozaRunner.from_config_file(
                str(mapping_config),
                output_format=OutputFormat.passthrough,
            )
            try:
                map_runner.run()
                data = map_runner.writer.result()
                assert isinstance(data, list)
            except NoTransformException:
                data = map_runner.data

            mapping_entry: dict[str, dict[str, str]] = {}
            key_column: str | None = map_runner.extra_transform_fields.get("key", None)
            value_columns: list[str] | None = map_runner.extra_transform_fields.get("values", None)

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
        base_directory: Path,
        output_dir: str = "",
        row_limit: int = 0,
        show_progress: bool = False,
    ):
        module_name: str | None = None
        transform_module: ModuleType | None = None

        if config.transform.code:
            transform_code_path = Path(config.transform.code)
            if not transform_code_path.is_absolute():
                transform_code_path = base_directory / transform_code_path
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

        on_data_begin = None
        on_data_end = None

        if transform_module is not None:
            module_contents = list(transform_module.__dict__.values())
            transform_single_fns = get_instances(decorators.KozaSingleTransformFunction, module_contents)
            transform_serial_fns = get_instances(decorators.KozaSerialTransformFunction, module_contents)
            on_data_begin_fns = get_instances(decorators.KozaDataBeginFunction, module_contents)
            on_data_end_fns = get_instances(decorators.KozaDataEndFunction, module_contents)

            def _on_data_begin(koza: KozaTransform):
                for fn in on_data_begin_fns:
                    fn(koza)

            def _on_data_end(koza: KozaTransform):
                for fn in on_data_end_fns:
                    fn(koza)

            on_data_begin = _on_data_begin if on_data_begin_fns else None
            on_data_end = _on_data_end if on_data_end_fns else None

            if len(transform_single_fns) > 1:
                raise ValueError("Only mark one function with `@koza.transform`")

            if len(transform_serial_fns) > 1:
                raise ValueError("Only mark one function with `@koza.transform_record`")

            transform = transform_single_fns[0] if transform_single_fns else None
            transform_record = transform_serial_fns[0] if transform_serial_fns else None

            if transform and transform_record:
                raise ValueError("Use one of `@koza.transform` or `@koza.transform_record`, not both")

            if transform is None and transform_record is None:
                raise NoTransformException(
                    "Must mark one function with either `@koza.transform_record` or `@koza.transform`"
                )

            if transform:
                logger.debug(f"Found transform function `{module_name}.{transform.fn.__name__}`")
            if transform_record:
                logger.debug(f"Found transform record function `{module_name}.{transform_record.fn.__name__}`")
        else:
            transform = None
            transform_record = None
            on_data_begin = None
            on_data_end = None

        source = Source(config, base_directory, row_limit=row_limit, show_progress=show_progress)

        writer: KozaWriter | None = None

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
            base_directory=base_directory,
            mapping_filenames=config.transform.mappings,
            extra_transform_fields=config.transform.extra_fields,
            transform=transform,
            transform_record=transform_record,
            on_data_begin=on_data_begin,
            on_data_end=on_data_end,
        )

    @classmethod
    def from_config_file(
        cls,
        config_filename: str,
        output_dir: str = "",
        output_format: OutputFormat | None = None,
        row_limit: int = 0,
        show_progress: bool = False,
        overrides: dict | None = None,
    ):
        transform_code_path: Path | None = None
        config_path = Path(config_filename)

        logger.info(f"Loading configuration from `{config_filename}`")

        with config_path.open("r") as fh:
            config_dict = yaml.load(fh, Loader=UniqueIncludeLoader.with_file_base(str(config_path)))  # noqa: S506
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
                transform_code_path = Path(mirrored_path.name)
            elif transform_literal_path.exists():
                transform_code_path = Path(transform_literal_path.name)

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

        return config, cls.from_config(
            config,
            base_directory=config_path.parent,
            output_dir=output_dir,
            row_limit=row_limit,
            show_progress=show_progress,
        )
